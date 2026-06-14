from __future__ import annotations

from collections.abc import Iterable


def is_original_app_running(process_names: Iterable[str]) -> bool:
    return any(name.casefold() == "nolliergb.exe" for name in process_names)


def is_gcc_running(process_names: Iterable[str]) -> bool:
    return any(name.casefold() == "gcc.exe" for name in process_names)


def running_process_names() -> list[str]:
    import psutil

    names: list[str] = []
    for process in psutil.process_iter(["name"]):
        try:
            name = process.info.get("name")
            if name:
                names.append(str(name))
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    return names


def original_app_running() -> bool:
    return is_original_app_running(running_process_names())


def gcc_running() -> bool:
    return is_gcc_running(running_process_names())
