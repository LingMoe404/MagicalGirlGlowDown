from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess

import pytest

from magical_girl_glow_down import security_paths
from magical_girl_glow_down.security_paths import (
    ensure_protected_directory,
    is_protected_install_path,
    program_files_roots,
    protected_data_dir,
)


def test_protected_data_dir_ignores_programdata_env(monkeypatch) -> None:
    monkeypatch.setenv("PROGRAMDATA", r"C:\Attacker\Data")
    monkeypatch.setattr(
        "magical_girl_glow_down.security_paths.program_data_root",
        lambda: Path(r"C:\Trusted\ProgramData"),
    )

    assert protected_data_dir() == Path(r"C:\Trusted\ProgramData\MagicalGirlGlowDown")


def test_program_files_roots_ignore_env_spoof(monkeypatch) -> None:
    monkeypatch.setenv("PROGRAMFILES", r"C:\Attacker\Program Files")
    monkeypatch.setenv("PROGRAMFILES(X86)", r"C:\Attacker\Program Files (x86)")
    monkeypatch.setattr(
        "magical_girl_glow_down.security_paths._known_folder_path",
        lambda folder_id: (
            Path(r"C:\Program Files")
            if folder_id is security_paths.FOLDERID_PROGRAM_FILES_X64
            or folder_id is security_paths.FOLDERID_PROGRAM_FILES
            else Path(r"C:\Program Files (x86)")
        ),
    )

    roots = program_files_roots()

    assert roots == (Path(r"C:\Program Files"), Path(r"C:\Program Files (x86)"))
    assert is_protected_install_path(Path(r"C:\Program Files\MagicalGirlGlowDown.exe"))
    assert not is_protected_install_path(Path(r"C:\Users\Alice\Downloads\MagicalGirlGlowDown.exe"))


def test_protected_directory_applies_acl_without_command_injection(tmp_path) -> None:
    calls: list[tuple[str, ...]] = []

    def run(command, **options):
        calls.append(tuple(command))
        return CompletedProcess(command, 0, "", "")

    target = tmp_path / "O'Malley" / "protected"
    ensure_protected_directory(target, run=run)

    assert target.is_dir()
    assert calls
    command = calls[0]
    assert command[0] == "icacls.exe"
    assert command[1] == str(target)
    assert "-Command" not in command


def test_protected_directory_rejects_parent_reparse_point(tmp_path, monkeypatch) -> None:
    parent = tmp_path / "parent"
    target = parent / "protected"
    parent.mkdir()
    monkeypatch.setattr(
        "magical_girl_glow_down.security_paths._is_reparse_point",
        lambda path: Path(path) == parent,
    )

    with pytest.raises(OSError, match="reparse point"):
        ensure_protected_directory(target)
