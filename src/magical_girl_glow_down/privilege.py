from __future__ import annotations

import ctypes
import subprocess
from collections.abc import Sequence

from .runtime import runtime_command


def requires_elevation(
    *,
    simulate: bool,
    gigabyte_probe: bool,
    install_autostart: bool,
    remove_autostart: bool,
    gigabyte_snapshot: bool = False,
    gigabyte_test_all: bool = False,
) -> bool:
    return install_autostart or remove_autostart or not (simulate or gigabyte_probe)


def is_elevated() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def relaunch_elevated(arguments: Sequence[str]) -> bool:
    executable, *argument_list = runtime_command(arguments)
    parameters = subprocess.list2cmdline(argument_list)
    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        executable,
        parameters,
        None,
        1,
    )
    return int(result) > 32
