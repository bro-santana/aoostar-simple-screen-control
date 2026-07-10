import argparse
import tkinter as tk

import pystray
from PIL import Image, ImageDraw

from app_config import AppConfig
from gui import MainWindow
from screen_worker import ScreenWorker

APP_NAME = "AOOSTAR Screen Control"


def make_tray_image():
    """Draws a small screen-shaped tray icon (no external assets needed)."""
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((2, 14, 62, 50), radius=8, fill=(30, 30, 34), outline=(90, 200, 250), width=3)
    draw.rectangle((12, 38, 52, 42), fill=(90, 200, 250))
    draw.ellipse((12, 22, 24, 34), outline=(90, 200, 250), width=3)
    draw.rectangle((32, 22, 52, 26), fill=(120, 120, 130))
    draw.rectangle((32, 30, 46, 34), fill=(120, 120, 130))
    return image


def make_tray_icon(window, worker):
    def toggle_pause(icon, _item):
        worker.set_paused(not worker.status()["paused"])
        icon.update_menu()

    menu = pystray.Menu(
        pystray.MenuItem("Open", lambda: window.post("show"), default=True),
        pystray.MenuItem("Pause updates", toggle_pause,
                         checked=lambda _item: worker.status()["paused"]),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Screen on", lambda: worker.set_screen(True)),
        pystray.MenuItem("Screen off", lambda: worker.set_screen(False)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", lambda: window.post("quit")),
    )
    return pystray.Icon("aoostar_screen_control", make_tray_image(), APP_NAME, menu)


def main():
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--minimized", action="store_true",
                        help="Start hidden in the system tray")
    args = parser.parse_args()

    config = AppConfig()

    worker = ScreenWorker(config)
    worker.start()

    root = tk.Tk()
    window = MainWindow(root, config, worker, on_quit=root.destroy)

    icon = make_tray_icon(window, worker)
    icon.run_detached()

    if args.minimized:
        root.withdraw()

    try:
        root.mainloop()
    finally:
        icon.visible = False
        icon.stop()
        worker.stop(screen_off=config.get("screen_off_on_exit"))
        worker.join(timeout=15)


if __name__ == "__main__":
    main()
