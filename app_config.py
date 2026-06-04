import json
import os
import sys
from pathlib import Path

APP_NAME = "Thermal-Imaging-Receiver"
DEFAULT_BAUDRATE = 921600
DEFAULT_REC_INTERVAL = 0.25


def default_data_dir():
    if sys.platform == "win32":
        base = Path(os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.getenv("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / APP_NAME / "data"


def default_config_path():
    if sys.platform == "win32":
        base = Path(os.getenv("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Preferences"
    else:
        base = Path(os.getenv("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / APP_NAME / "config.json"


def load_config(path=None, create_data_dir=False):
    config_path = Path(path) if path else default_config_path()
    config = {
        "baudrate": DEFAULT_BAUDRATE,
        "record_interval": DEFAULT_REC_INTERVAL,
        "data_dir": str(default_data_dir()),
    }

    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as file:
                loaded = json.load(file)
            if isinstance(loaded, dict):
                config.update({k: v for k, v in loaded.items() if v is not None})
        except (OSError, json.JSONDecodeError):
            pass

    data_dir = Path(config["data_dir"]).expanduser()
    if create_data_dir:
        data_dir.mkdir(parents=True, exist_ok=True)
    config["data_dir"] = data_dir
    return config
