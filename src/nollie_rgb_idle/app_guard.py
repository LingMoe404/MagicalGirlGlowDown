from __future__ import annotations

from collections.abc import Iterable


def is_original_app_running(process_names: Iterable[str]) -> bool:
    return any(name.casefold() == "nolliergb.exe" for name in process_names)


def original_app_running() -> bool:
    import psutil

    names: list[str] = []
    for process in psutil.process_iter(["name"]):
        try:
            name = process.info.get("name")
            if name:
                names.append(str(name))
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    return is_original_app_running(names)
