from pathlib import Path
from subprocess import CompletedProcess

import pytest

from magical_girl_glow_down.security_paths import (
    ensure_protected_directory,
    is_protected_install_path,
    protected_data_dir,
)


def test_protected_data_dir_uses_programdata(monkeypatch) -> None:
    monkeypatch.setenv("PROGRAMDATA", r"C:\ProgramData")
    assert protected_data_dir() == Path(r"C:\ProgramData\MagicalGirlGlowDown")


def test_protected_directory_applies_admin_and_system_acl(tmp_path) -> None:
    calls: list[tuple[str, ...]] = []

    def run(command, **options):
        calls.append(tuple(command))
        return CompletedProcess(command, 0, "", "")

    target = tmp_path / "protected"
    ensure_protected_directory(target, run=run)

    assert target.is_dir()
    flattened = " ".join(part for command in calls for part in command)
    assert "(A;OICI;FA;;;SY)" in flattened
    assert "(A;OICI;FA;;;BA)" in flattened


def test_protected_directory_rejects_reparse_point(tmp_path, monkeypatch) -> None:
    target = tmp_path / "protected"
    target.mkdir()
    monkeypatch.setattr("os.path.isjunction", lambda path: Path(path) == target)

    with pytest.raises(OSError, match="reparse point"):
        ensure_protected_directory(target)


def test_program_files_path_is_protected() -> None:
    assert is_protected_install_path(
        Path(r"C:\Program Files\MagicalGirlGlowDown\MagicalGirlGlowDown.exe"),
        (Path(r"C:\Program Files"), Path(r"C:\Program Files (x86)")),
    )
    assert not is_protected_install_path(
        Path(r"C:\Users\Alice\Downloads\MagicalGirlGlowDown.exe"),
        (Path(r"C:\Program Files"), Path(r"C:\Program Files (x86)")),
    )
