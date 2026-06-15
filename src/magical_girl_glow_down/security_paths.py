from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from .branding import DATA_DIR_NAME

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
PROTECTED_DIRECTORY_SDDL = (
    "O:BAG:BAD:P"
    "(A;OICI;FA;;;SY)"
    "(A;OICI;FA;;;BA)"
)


def protected_data_dir() -> Path:
    root = os.getenv("PROGRAMDATA")
    if not root:
        raise OSError("PROGRAMDATA is unavailable")
    return Path(root) / DATA_DIR_NAME


def _is_reparse_point(path: Path) -> bool:
    return path.is_symlink() or os.path.isjunction(path)


def ensure_protected_directory(
    path: Path,
    *,
    run: CommandRunner = subprocess.run,
) -> None:
    if path.exists() and _is_reparse_point(path):
        raise OSError(f"protected path is a reparse point: {path}")
    path.mkdir(parents=True, exist_ok=True)
    if _is_reparse_point(path):
        raise OSError(f"protected path is a reparse point: {path}")
    script = (
        f"& {{ "
        f"$ErrorActionPreference = 'Stop'; "
        f"$acl = New-Object System.Security.AccessControl.DirectorySecurity; "
        f"$acl.SetSecurityDescriptorSddlForm('{PROTECTED_DIRECTORY_SDDL}'); "
        f"Set-Acl -LiteralPath '{path}' -AclObject $acl"
        f" }}"
    )
    command = (
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
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
    candidates = roots or tuple(
        Path(value)
        for value in (
            os.getenv("PROGRAMFILES"),
            os.getenv("PROGRAMFILES(X86)"),
        )
        if value
    )
    resolved = executable.resolve(strict=False)
    return any(resolved.is_relative_to(root.resolve(strict=False)) for root in candidates)
