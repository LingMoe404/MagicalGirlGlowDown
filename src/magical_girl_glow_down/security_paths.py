from __future__ import annotations

import ctypes
import os
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from .branding import DATA_DIR_NAME

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]

FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def _guid(data1: int, data2: int, data3: int, data4: Sequence[int]) -> GUID:
    return GUID(data1, data2, data3, (ctypes.c_ubyte * 8)(*data4))


FOLDERID_PROGRAM_DATA = _guid(
    0x62AB5D82,
    0xFDC1,
    0x4DC3,
    (0xA9, 0xDD, 0x07, 0x0D, 0x1D, 0x49, 0x5D, 0x97),
)
FOLDERID_PROGRAM_FILES = _guid(
    0x905E63B6,
    0xC1BF,
    0x494E,
    (0xB2, 0x9C, 0x65, 0xB7, 0x32, 0xD3, 0xD2, 0x1A),
)
FOLDERID_PROGRAM_FILES_X64 = _guid(
    0x6D809377,
    0x6AF0,
    0x444B,
    (0x89, 0x57, 0xA3, 0x77, 0x3F, 0x02, 0x20, 0x0E),
)
FOLDERID_PROGRAM_FILES_X86 = _guid(
    0x7C5A40EF,
    0xA0FB,
    0x4BFC,
    (0x87, 0x4A, 0xC0, 0xF2, 0xE0, 0xB9, 0xFA, 0x8E),
)

SYSTEM_SID = "*S-1-5-18"
ADMINISTRATORS_SID = "*S-1-5-32-544"


def _known_folder_path(folder_id: GUID) -> Path:
    if os.name != "nt":  # pragma: no cover - the application is Windows-only.
        raise OSError("Windows known folders are unavailable")
    path_ptr = ctypes.c_void_p()
    result = ctypes.windll.shell32.SHGetKnownFolderPath(
        ctypes.byref(folder_id),
        0,
        None,
        ctypes.byref(path_ptr),
    )
    if result != 0 or not path_ptr.value:
        raise OSError(ctypes.WinError(result))
    try:
        return Path(ctypes.wstring_at(path_ptr.value))
    finally:
        ctypes.windll.ole32.CoTaskMemFree(path_ptr)


def program_data_root() -> Path:
    return _known_folder_path(FOLDERID_PROGRAM_DATA)


def program_files_roots() -> tuple[Path, ...]:
    roots: list[Path] = []
    for folder_id in (
        FOLDERID_PROGRAM_FILES_X64,
        FOLDERID_PROGRAM_FILES_X86,
        FOLDERID_PROGRAM_FILES,
    ):
        try:
            root = _known_folder_path(folder_id)
        except OSError:
            continue
        if root not in roots:
            roots.append(root)
    if not roots:
        raise OSError("Program Files known folders are unavailable")
    return tuple(roots)


def protected_data_dir() -> Path:
    return program_data_root() / DATA_DIR_NAME


def _path_chain(path: Path) -> Sequence[Path]:
    chain: list[Path] = [path]
    current = path
    while current.parent != current:
        current = current.parent
        chain.append(current)
    return chain


def _is_reparse_point(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(os.path, "isjunction", None)
    if callable(is_junction) and is_junction(path):
        return True
    if os.name != "nt":  # pragma: no cover - the application is Windows-only.
        return False
    attributes = ctypes.windll.kernel32.GetFileAttributesW(str(path))
    return attributes != INVALID_FILE_ATTRIBUTES and bool(
        int(attributes) & FILE_ATTRIBUTE_REPARSE_POINT
    )


def _ensure_no_reparse_points(path: Path) -> None:
    for candidate in _path_chain(path):
        if candidate.exists() and _is_reparse_point(candidate):
            raise OSError(f"protected path is a reparse point: {candidate}")


def ensure_protected_directory(
    path: Path,
    *,
    run: CommandRunner = subprocess.run,
) -> None:
    _ensure_no_reparse_points(path)
    path.mkdir(parents=True, exist_ok=True)
    _ensure_no_reparse_points(path)

    command = (
        "icacls.exe",
        str(path),
        "/inheritance:r",
        "/grant:r",
        f"{SYSTEM_SID}:(OI)(CI)F",
        f"{ADMINISTRATORS_SID}:(OI)(CI)F",
    )
    result = run(
        command,
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
        check=False,
    )
    if result.returncode != 0:
        raise OSError(result.stderr.strip() or "could not protect ProgramData directory")


def is_protected_install_path(
    executable: Path,
    roots: Sequence[Path] | None = None,
) -> bool:
    candidates = roots or program_files_roots()
    resolved = executable.resolve(strict=False)
    return any(resolved.is_relative_to(root.resolve(strict=False)) for root in candidates)
