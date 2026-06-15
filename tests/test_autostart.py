from __future__ import annotations

from magical_girl_glow_down.autostart import AutostartManager


class FakeTaskScheduler:
    def __init__(self) -> None:
        self.command: str | None = None

    def create(self, command: str) -> None:
        self.command = command

    def delete(self) -> None:
        self.command = None

    def exists(self) -> bool:
        return self.command is not None


def test_autostart_is_reversible() -> None:
    scheduler = FakeTaskScheduler()
    manager = AutostartManager(scheduler, "uv run magical-girl-glow-down")
    manager.enable()
    assert manager.enabled()
    manager.disable()
    assert not manager.enabled()


def test_portable_autostart_requires_confirmation() -> None:
    from pathlib import Path

    from magical_girl_glow_down.autostart import requires_portable_confirmation

    assert requires_portable_confirmation(
        Path(r"C:\Users\Alice\Downloads\MagicalGirlGlowDown.exe"),
        (Path(r"C:\Program Files"),),
    )


def test_program_files_autostart_does_not_require_confirmation() -> None:
    from pathlib import Path

    from magical_girl_glow_down.autostart import requires_portable_confirmation

    assert not requires_portable_confirmation(
        Path(r"C:\Program Files\MagicalGirlGlowDown\MagicalGirlGlowDown.exe"),
        (Path(r"C:\Program Files"),),
    )

