from __future__ import annotations

from magical_girl_glow_down.autostart import AutostartManager


class FakeRegistry:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def set(self, name: str, value: str) -> None:
        self.values[name] = value

    def delete(self, name: str) -> None:
        self.values.pop(name, None)

    def get(self, name: str) -> str | None:
        return self.values.get(name)


def test_autostart_is_reversible() -> None:
    registry = FakeRegistry()
    manager = AutostartManager(registry, "uv run magical-girl-glow-down")
    manager.enable()
    assert manager.enabled()
    manager.disable()
    assert not manager.enabled()
