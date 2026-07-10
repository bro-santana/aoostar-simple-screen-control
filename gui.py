import queue
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image, ImageTk

import autostart
from aoostar_screen import WIDTH, HEIGHT, load_monitor_config, render_aoostar_panel

THUMB_WIDTH = 220
THUMB_HEIGHT = round(THUMB_WIDTH * HEIGHT / WIDTH)
PANELS_PER_ROW = 4


class MainWindow:
    """Configuration window. Closing it hides to the tray instead of quitting."""

    def __init__(self, root, config, worker, on_quit):
        self.root = root
        self.config = config
        self.worker = worker
        self.on_quit = on_quit
        self._ui_queue = queue.Queue()
        self._thumbnails = []      # keep PhotoImage references alive
        self._panel_vars = {}      # panel_id -> BooleanVar (in rotation)

        root.title("AOOSTAR Screen Control")
        root.resizable(False, False)
        root.protocol("WM_DELETE_WINDOW", self.hide)

        self._build_settings_vars()
        self._build_widgets()
        self.reload_panels()
        self._poll()

    # ----- thread-safe entry point for the tray icon -----

    def post(self, action):
        """Queue an action ('show' or 'quit') from another thread."""
        self._ui_queue.put(action)

    # ----- window construction -----

    def _build_settings_vars(self):
        cfg = self.config.snapshot()
        self.var_refresh = tk.IntVar(value=cfg["refresh_seconds"])
        self.var_switch = tk.IntVar(value=cfg["switch_seconds"])
        self.var_hwinfo = tk.BooleanVar(value=cfg["use_hwinfo"])
        self.var_off_on_exit = tk.BooleanVar(value=cfg["screen_off_on_exit"])
        self.var_autostart = tk.BooleanVar(value=autostart.is_enabled())
        self.var_data_path = tk.StringVar(value=cfg["data_path"])
        self.var_paused = tk.BooleanVar(value=False)

    def _build_widgets(self):
        main = ttk.Frame(self.root, padding=10)
        main.grid(sticky="nsew")

        self.panels_frame = ttk.LabelFrame(main, text="Panels", padding=8)
        self.panels_frame.grid(row=0, column=0, sticky="ew")

        settings = ttk.LabelFrame(main, text="Settings", padding=8)
        settings.grid(row=1, column=0, sticky="ew", pady=(10, 0))

        ttk.Label(settings, text="Refresh data every").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(settings, from_=1, to=3600, width=6,
                    textvariable=self.var_refresh).grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(settings, text="s").grid(row=0, column=2, sticky="w")

        ttk.Label(settings, text="Switch panel every").grid(row=0, column=3, sticky="w", padx=(20, 0))
        ttk.Spinbox(settings, from_=5, to=86400, width=6,
                    textvariable=self.var_switch).grid(row=0, column=4, sticky="w", padx=4)
        ttk.Label(settings, text="s").grid(row=0, column=5, sticky="w")

        ttk.Checkbutton(settings, text="Use HWiNFO sensor data",
                        variable=self.var_hwinfo).grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))
        ttk.Checkbutton(settings, text="Turn screen off on exit",
                        variable=self.var_off_on_exit).grid(row=1, column=3, columnspan=3, sticky="w", pady=(6, 0))
        ttk.Checkbutton(settings, text="Start with Windows (minimized to tray)",
                        variable=self.var_autostart).grid(row=2, column=0, columnspan=4, sticky="w", pady=(4, 0))

        ttk.Label(settings, text="Data path").grid(row=3, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(settings, textvariable=self.var_data_path, width=52).grid(
            row=3, column=1, columnspan=4, sticky="we", padx=4, pady=(6, 0))
        ttk.Button(settings, text="Browse...", command=self._browse_data_path).grid(
            row=3, column=5, sticky="w", pady=(6, 0))

        ttk.Button(settings, text="Apply & Save", command=self.apply_settings).grid(
            row=4, column=0, columnspan=6, sticky="e", pady=(8, 0))

        controls = ttk.Frame(main)
        controls.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(controls, text="Screen on",
                   command=lambda: self.worker.set_screen(True)).grid(row=0, column=0)
        ttk.Button(controls, text="Screen off",
                   command=lambda: self.worker.set_screen(False)).grid(row=0, column=1, padx=6)
        self.pause_button = ttk.Button(controls, text="Pause updates", command=self._toggle_pause)
        self.pause_button.grid(row=0, column=2)
        ttk.Button(controls, text="Hide to tray", command=self.hide).grid(row=0, column=3, padx=6)

        self.status_label = ttk.Label(main, text="Starting...", foreground="gray")
        self.status_label.grid(row=3, column=0, sticky="w", pady=(8, 0))

    def reload_panels(self):
        for child in self.panels_frame.winfo_children():
            child.destroy()
        self._thumbnails.clear()
        self._panel_vars.clear()

        data_path = self.var_data_path.get()
        try:
            monitor = load_monitor_config(data_path)
            panel_count = len(monitor["diy"])
        except Exception as e:
            ttk.Label(self.panels_frame,
                      text=f"Could not load panels from data path:\n{e}").grid()
            return

        rotation = set(int(p) for p in self.config.get("rotation_panels"))

        for i in range(panel_count):
            panel_id = i + 1
            cell = ttk.Frame(self.panels_frame, padding=4)
            cell.grid(row=i // PANELS_PER_ROW, column=i % PANELS_PER_ROW)

            try:
                image = render_aoostar_panel(panel_id, None, data_path)
                image.thumbnail((THUMB_WIDTH, THUMB_HEIGHT))
                photo = ImageTk.PhotoImage(image)
            except Exception:
                placeholder = Image.new("RGB", (THUMB_WIDTH, THUMB_HEIGHT), "#333333")
                photo = ImageTk.PhotoImage(placeholder)
            self._thumbnails.append(photo)

            thumb = ttk.Label(cell, image=photo, cursor="hand2")
            thumb.grid(row=0, column=0, columnspan=2)
            thumb.bind("<Button-1>", lambda _e, p=panel_id: self.worker.show_panel(p))

            var = tk.BooleanVar(value=panel_id in rotation)
            self._panel_vars[panel_id] = var
            ttk.Checkbutton(cell, text=f"Panel {panel_id} in rotation",
                            variable=var).grid(row=1, column=0, sticky="w")
            ttk.Button(cell, text="Show now",
                       command=lambda p=panel_id: self.worker.show_panel(p)).grid(row=1, column=1, sticky="e")

    # ----- actions -----

    def _browse_data_path(self):
        chosen = filedialog.askdirectory(initialdir=self.var_data_path.get(),
                                         title="Select Aoostar-X compatible data folder")
        if chosen:
            self.var_data_path.set(chosen)
            self.reload_panels()

    def apply_settings(self):
        rotation = [p for p, var in self._panel_vars.items() if var.get()]
        try:
            self.config.update(
                refresh_seconds=max(1, int(self.var_refresh.get())),
                switch_seconds=max(5, int(self.var_switch.get())),
                use_hwinfo=self.var_hwinfo.get(),
                screen_off_on_exit=self.var_off_on_exit.get(),
                data_path=self.var_data_path.get(),
                rotation_panels=rotation,
            )
            self.config.save()
        except (tk.TclError, ValueError) as e:
            messagebox.showerror("Invalid settings", str(e))
            return
        try:
            autostart.set_enabled(self.var_autostart.get())
        except OSError as e:
            messagebox.showwarning("Autostart", f"Could not update autostart entry:\n{e}")
        self.reload_panels()
        self.worker.config_changed()

    def _toggle_pause(self):
        paused = not self.var_paused.get()
        self.var_paused.set(paused)
        self.worker.set_paused(paused)

    def show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide(self):
        self.root.withdraw()

    # ----- periodic UI update -----

    def _poll(self):
        while True:
            try:
                action = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            if action == "show":
                self.show()
            elif action == "quit":
                self.on_quit()
                return

        status = self.worker.status()
        parts = []
        parts.append(f"Device: {status['port']}" if status["connected"] else "Device: not connected")
        if status["hwinfo"] is True:
            parts.append("HWiNFO: OK")
        elif status["hwinfo"] is False:
            parts.append("HWiNFO: not available")
        if status["last_sent"]:
            parts.append(f"Last frame: {time.strftime('%H:%M:%S', time.localtime(status['last_sent']))}")
        if status["message"]:
            parts.append(status["message"])
        self.status_label.config(text=" | ".join(parts))
        self.pause_button.config(text="Resume updates" if status["paused"] else "Pause updates")

        self.root.after(500, self._poll)
