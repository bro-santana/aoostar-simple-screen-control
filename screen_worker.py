import queue
import threading
import time

import serial

import aoostar_screen
from aoostar_screen import (
    find_serial_port,
    lcd_on,
    lcd_off,
    render_aoostar_panel,
    send_image,
)
from hwinfo_data import getHWiNFOData, convertHWiNFODataToAoostarCompatible


class ScreenWorker(threading.Thread):
    """Background thread that keeps the mini PC screen updated.

    Owns the serial connection. Refreshes the current panel with fresh sensor
    data every `refresh_seconds` and advances through `rotation_panels` every
    `switch_seconds`. The GUI/tray talk to it only through the command queue
    and the status() snapshot, never through the serial port directly.
    """

    def __init__(self, config):
        super().__init__(name="ScreenWorker", daemon=True)
        self.config = config
        self._commands = queue.Queue()
        self._ser = None
        self._paused = False
        self._current_panel = None
        self._status_lock = threading.Lock()
        self._status = {
            "connected": False,
            "port": None,
            "hwinfo": None,       # None = not tried yet, True/False afterwards
            "current_panel": None,
            "paused": False,
            "message": "Starting...",
            "last_sent": None,    # time.time() of last successful frame
        }
        aoostar_screen.VERBOSE = False

    # ----- public API (safe to call from any thread) -----

    def status(self) -> dict:
        with self._status_lock:
            return dict(self._status)

    def show_panel(self, panel_id: int):
        self._commands.put(("show", panel_id))

    def set_screen(self, on: bool):
        self._commands.put(("lcd", on))

    def set_paused(self, paused: bool):
        self._commands.put(("pause", paused))

    def config_changed(self):
        self._commands.put(("config", None))

    def stop(self, screen_off=False):
        self._commands.put(("stop", screen_off))

    # ----- internals (worker thread only) -----

    def _set_status(self, **kwargs):
        with self._status_lock:
            self._status.update(kwargs)

    def _ensure_serial(self):
        if self._ser is not None and self._ser.is_open:
            return
        port = find_serial_port()
        if port is None:
            raise serial.SerialException("Screen device not found (is it connected?)")
        self._ser = serial.Serial(port,
                                  baudrate=1500000,
                                  parity=serial.PARITY_NONE,
                                  stopbits=serial.STOPBITS_ONE,
                                  bytesize=serial.EIGHTBITS,
                                  timeout=2.0)
        lcd_on(self._ser)
        self._set_status(connected=True, port=port, message=f"Connected on {port}")

    def _drop_serial(self):
        if self._ser is not None:
            try:
                self._ser.close()
            except Exception:
                pass
            self._ser = None
        self._set_status(connected=False, port=None)

    def _get_sensor_data(self, cfg):
        if not cfg["use_hwinfo"]:
            self._set_status(hwinfo=None)
            return None
        try:
            snapshot = getHWiNFOData()
            if snapshot and "error" not in snapshot:
                data = convertHWiNFODataToAoostarCompatible(snapshot)
                self._set_status(hwinfo=True)
                return data
        except Exception:
            pass
        self._set_status(hwinfo=False)
        return None

    def _send_panel(self, panel_id, cfg):
        try:
            self._ensure_serial()
        except serial.SerialException as e:
            self._drop_serial()
            self._set_status(message=str(e))
            return False

        sensor_data = self._get_sensor_data(cfg)
        try:
            image = render_aoostar_panel(panel_id, sensor_data, cfg["data_path"])
        except Exception as e:
            self._set_status(message=f"Panel {panel_id} render failed: {e}")
            return False

        try:
            send_image(self._ser, image)
        except Exception as e:
            self._drop_serial()
            self._set_status(message=f"Send failed: {e}")
            return False

        self._set_status(current_panel=panel_id, last_sent=time.time(),
                         message=f"Panel {panel_id} sent")
        return True

    def _set_lcd(self, on):
        try:
            self._ensure_serial()
            if on:
                lcd_on(self._ser)
            else:
                lcd_off(self._ser)
            self._set_status(message=f"Screen turned {'on' if on else 'off'}")
        except (serial.SerialException, IOError) as e:
            self._drop_serial()
            self._set_status(message=f"Screen command failed: {e}")

    def _next_panel(self, rotation):
        if self._current_panel in rotation:
            index = (rotation.index(self._current_panel) + 1) % len(rotation)
        else:
            index = 0
        return rotation[index]

    def run(self):
        now = time.monotonic()
        next_refresh = now   # send first frame immediately
        next_switch = now + self.config.get("switch_seconds")
        screen_off_on_exit = False

        while True:
            try:
                command, value = self._commands.get(timeout=0.5)
            except queue.Empty:
                command, value = None, None

            cfg = self.config.snapshot()

            if command == "stop":
                screen_off_on_exit = value
                break
            elif command == "show":
                self._current_panel = value
                next_refresh = time.monotonic()
                next_switch = time.monotonic() + cfg["switch_seconds"]
            elif command == "pause":
                self._paused = value
                self._set_status(paused=value,
                                 message="Paused" if value else "Resumed")
                if not value:
                    next_refresh = time.monotonic()
            elif command == "lcd":
                self._set_lcd(value)
                continue
            elif command == "config":
                next_refresh = time.monotonic()
                next_switch = time.monotonic() + cfg["switch_seconds"]

            if self._paused:
                continue

            rotation = [int(p) for p in cfg["rotation_panels"]] or [1]
            if self._current_panel is None:
                self._current_panel = rotation[0]

            now = time.monotonic()
            if now >= next_switch:
                if len(rotation) > 1:
                    self._current_panel = self._next_panel(rotation)
                    next_refresh = now
                next_switch = now + cfg["switch_seconds"]

            if now >= next_refresh:
                try:
                    self._send_panel(self._current_panel, cfg)
                except Exception as e:
                    # Never let an unexpected error kill the worker thread
                    self._drop_serial()
                    self._set_status(message=f"Update failed: {e}")
                next_refresh = time.monotonic() + cfg["refresh_seconds"]

        if screen_off_on_exit:
            self._set_lcd(False)
        self._drop_serial()
        self._set_status(message="Stopped")
