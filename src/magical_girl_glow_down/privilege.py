from __future__ import annotations

import ctypes
import subprocess
import sys
from collections.abc import Sequence

from .branding import MODULE_ENTRY


def requires_elevation(
    *,
    simulate: bool,
    gigabyte_probe: bool,
    install_autostart: bool,
    remove_autostart: bool,
    gigabyte_snapshot: bool = False,
    gigabyte_test_all: bool = False,
) -> bool:
    return not (simulate or gigabyte_probe or install_autostart or remove_autostart)


def is_elevated() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def relaunch_elevated(arguments: Sequence[str]) -> bool:
    parameters = subprocess.list2cmdline(["-m", MODULE_ENTRY, *arguments])
    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        sys.executable,
        parameters,
        None,
        1,
    )
    return int(result) > 32
