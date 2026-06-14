from __future__ import annotations

from magical_girl_glow_down.autostart import (
    LEGACY_VALUE_NAME,
    VALUE_NAME,
    AutostartManager,
)


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


def test_autostart_migrates_legacy_value() -> None:
    registry = FakeRegistry()
    registry.values[LEGACY_VALUE_NAME] = "old command"
    manager = AutostartManager(registry, "uv run magical-girl-glow-down")

    manager.migrate_legacy()

    assert registry.values == {VALUE_NAME: "uv run magical-girl-glow-down"}


def test_disable_removes_current_and_legacy_values() -> None:
    registry = FakeRegistry()
    registry.values[VALUE_NAME] = "new command"
    registry.values[LEGACY_VALUE_NAME] = "old command"
    manager = AutostartManager(registry, "new command")

    manager.disable()

    assert registry.values == {}
