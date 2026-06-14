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
