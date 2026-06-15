from __future__ import annotations

import ctypes
from collections.abc import Iterable
from ctypes import wintypes

# Windows Constants
TH32CS_SNAPPROCESS = 0x00000002
INVALID_HANDLE_VALUE = -1


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


def is_process_running(target_name: str) -> bool:
    target_name_lower = target_name.casefold()

    kernel32 = ctypes.windll.kernel32
    h_snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if h_snapshot == INVALID_HANDLE_VALUE or h_snapshot is None:
        return False

    try:
        pe = PROCESSENTRY32W()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)

        if not kernel32.Process32FirstW(h_snapshot, ctypes.byref(pe)):
            return False

        while True:
            if pe.szExeFile.casefold() == target_name_lower:
                return True
            if not kernel32.Process32NextW(h_snapshot, ctypes.byref(pe)):
                break
    finally:
        kernel32.CloseHandle(h_snapshot)

    return False


def is_original_app_running(process_names: Iterable[str] | None = None) -> bool:
    if process_names is not None:
        return any(name.casefold() == "nolliergb.exe" for name in process_names)
    return is_process_running("nolliergb.exe")


def is_gcc_running(process_names: Iterable[str] | None = None) -> bool:
    if process_names is not None:
        return any(name.casefold() == "gcc.exe" for name in process_names)
    return is_process_running("gcc.exe")
