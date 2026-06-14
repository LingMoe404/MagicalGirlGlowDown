from __future__ import annotations

import ctypes
from contextlib import suppress
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

APP_NAME = "MagicalGirlGlowDown"
APP_DISPLAY_NAME = "魔法少女·静谧霓虹"
APP_ID = "LingMoe404.MagicalGirlGlowDown"
CLI_NAME = "magical-girl-glow-down"
DISTRIBUTION_NAME = "magical-girl-glow-down"
MODULE_ENTRY = "magical_girl_glow_down.main"

DATA_DIR_NAME = APP_NAME
AUTOSTART_VALUE_NAME = APP_NAME

# Compatibility identifiers from releases before the final product rename.
LEGACY_APP_NAME = "NollieRGBIdle"
LEGACY_HOME_DIR_NAME = ".nollie-rgb-idle"


def app_version() -> str:
    try:
        return version(DISTRIBUTION_NAME)
    except PackageNotFoundError:
        return "unknown"


def icon_path() -> Path:
    return Path(__file__).resolve().parent / "assets" / "logo.ico"


def set_windows_app_id() -> None:
    with suppress(AttributeError, OSError):
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
