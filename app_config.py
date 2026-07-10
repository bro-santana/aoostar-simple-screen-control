import json
import os
import threading

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
DEFAULT_DATA_PATH = os.path.join(APP_DIR, "aoostar-x-compatible-data")

DEFAULTS = {
    # Path with Monitor3.json, sys_img/ and fonts/ (Aoostar-X _internal compatible)
    "data_path": DEFAULT_DATA_PATH,
    # Panel ids (1-based) included in the automatic rotation
    "rotation_panels": [1, 2],
    # Seconds between switching to the next panel in the rotation
    "switch_seconds": 60,
    # Seconds between sensor-data refreshes of the current panel
    "refresh_seconds": 5,
    # Read live sensor values from HWiNFO shared memory
    "use_hwinfo": True,
    # Send the LCD off command when the app quits
    "screen_off_on_exit": False,
}


class AppConfig:
    """Thread-safe app settings persisted to config.json next to the app."""

    def __init__(self, path=CONFIG_PATH):
        self._path = path
        self._lock = threading.Lock()
        self._data = dict(DEFAULTS)
        self.load()

    def load(self):
        try:
            with open(self._path, 'r', encoding='utf-8') as f:
                stored = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return
        with self._lock:
            for key in DEFAULTS:
                if key in stored:
                    self._data[key] = stored[key]

    def save(self):
        with self._lock:
            data = dict(self._data)
        with open(self._path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def get(self, key):
        with self._lock:
            return self._data[key]

    def update(self, **kwargs):
        with self._lock:
            for key, value in kwargs.items():
                if key not in DEFAULTS:
                    raise KeyError(key)
                self._data[key] = value

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._data)
