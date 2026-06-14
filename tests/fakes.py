from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from nollie_rgb_idle.domain import ControllerId
from nollie_rgb_idle.lighting import TargetIdentity


@dataclass
class FakeController:
    identity: ControllerId
    brightness: list[int]
    fail_read: bool = False
    fail_write: bool = False

    async def read_standby_brightness(self) -> tuple[int, ...]:
        if self.fail_read:
            raise OSError("read failed")
        return tuple(self.brightness)

    async def write_standby_brightness(self, values: tuple[int, ...]) -> None:
        if self.fail_write:
            raise OSError("write failed")
        self.brightness[:] = values


class FakeLightingTarget:
    def __init__(self, backend: str, device: str, state: dict[str, object]) -> None:
        self.identity = TargetIdentity(backend, device)
        self.state = deepcopy(state)
        self.blackout_calls = 0
        self.restore_calls = 0

    async def snapshot(self) -> dict[str, object]:
        return deepcopy(self.state)

    async def blackout(self, snapshot: dict[str, object]) -> None:
        self.blackout_calls += 1
        canvases = snapshot.get("canvases")
        if isinstance(canvases, list):
            self.state = {"canvases": [0 for _ in canvases]}

    async def restore(self, snapshot: dict[str, object]) -> None:
        self.restore_calls += 1
        self.state = deepcopy(snapshot)
