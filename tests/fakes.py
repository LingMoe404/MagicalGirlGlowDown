from __future__ import annotations

from dataclasses import dataclass

from nollie_rgb_idle.domain import ControllerId


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
