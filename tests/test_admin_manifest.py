from __future__ import annotations

import ctypes
import shutil
import subprocess
from ctypes import wintypes
from pathlib import Path


def _read_manifest(path: Path) -> str:
    kernel32 = ctypes.windll.kernel32
    kernel32.LoadLibraryExW.argtypes = [ctypes.c_wchar_p, wintypes.HANDLE, wintypes.DWORD]
    kernel32.LoadLibraryExW.restype = wintypes.HMODULE
    kernel32.FindResourceW.argtypes = [wintypes.HMODULE, wintypes.LPCWSTR, wintypes.LPCWSTR]
    kernel32.FindResourceW.restype = wintypes.HRSRC
    kernel32.LoadResource.argtypes = [wintypes.HMODULE, wintypes.HRSRC]
    kernel32.LoadResource.restype = wintypes.HGLOBAL
    kernel32.LockResource.argtypes = [wintypes.HGLOBAL]
    kernel32.LockResource.restype = wintypes.LPVOID
    kernel32.SizeofResource.argtypes = [wintypes.HMODULE, wintypes.HRSRC]
    kernel32.SizeofResource.restype = wintypes.DWORD
    kernel32.FreeLibrary.argtypes = [wintypes.HMODULE]
    kernel32.FreeLibrary.restype = wintypes.BOOL

    load_library_as_datafile = 0x00000002
    module = kernel32.LoadLibraryExW(str(path), None, load_library_as_datafile)
    if not module:
        raise ctypes.WinError()
    try:
        resource = kernel32.FindResourceW(module, ctypes.c_wchar_p(1), ctypes.c_wchar_p(24))
        if not resource:
            raise ctypes.WinError()
        size = kernel32.SizeofResource(module, resource)
        data = kernel32.LoadResource(module, resource)
        pointer = kernel32.LockResource(data)
        if not pointer:
            raise ctypes.WinError()
        return ctypes.string_at(pointer, size).decode("utf-8-sig")
    finally:
        kernel32.FreeLibrary(module)


def test_set_admin_manifest_updates_requested_execution_level(tmp_path: Path) -> None:
    source = Path(
        r"A:\Code\MagicalGirlGlowDown\src\magical_girl_glow_down\gigabyte_helper\MagicalGirlGlowDown.GigabyteHelper.exe"
    )
    target = tmp_path / "helper.exe"
    shutil.copy2(source, target)

    script = Path(r"A:\Code\MagicalGirlGlowDown\scripts\set-admin-manifest.ps1")
    subprocess.run(
        [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-Path",
            str(target),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    manifest = _read_manifest(target)
    assert 'requestedExecutionLevel level="requireAdministrator"' in manifest
    assert 'requestedExecutionLevel level="asInvoker"' not in manifest
