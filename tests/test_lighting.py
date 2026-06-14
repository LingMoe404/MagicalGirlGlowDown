from __future__ import annotations

import pytest

from magical_girl_glow_down.domain import ControllerId
from magical_girl_glow_down.lighting import LightingError, LightingSnapshot, TargetIdentity
from magical_girl_glow_down.protocol import NollieLightingTarget

from .fakes import FakeController, FakeLightingTarget


class ValueErrorController:
    def __init__(
        self,
        model: str,
        serial: str,
        brightness: list[int],
        *,
        fail_read: bool = False,
        fail_write: bool = False,
    ) -> None:
        self.identity = ControllerId(model, serial)
        self.brightness = brightness
        self.fail_read = fail_read
        self.fail_write = fail_write

    async def read_standby_brightness(self) -> tuple[int, ...]:
        if self.fail_read:
            raise ValueError("bad controller read")
        return tuple(self.brightness)

    async def write_standby_brightness(self, values: tuple[int, ...]) -> None:
        if self.fail_write:
            raise ValueError("bad controller write")
        self.brightness[:] = values


def test_snapshot_round_trip_preserves_opaque_state() -> None:
    snapshot = LightingSnapshot(
        identity=TargetIdentity("nollie", "Nollie16:ABC"),
        state={"canvases": [30, 80], "metadata": {"profile": "standby"}},
        pending_restore=True,
    )

    assert LightingSnapshot.from_dict(snapshot.to_dict()) == snapshot
    assert snapshot.identity.key == "nollie:Nollie16:ABC"


async def test_fake_lighting_target_blackouts_and_restores_snapshot() -> None:
    target = FakeLightingTarget("nollie", "A", {"canvases": [30]})

    state = await target.snapshot()
    await target.blackout(state)
    assert target.state == {"canvases": [0]}

    await target.restore(state)
    assert target.state == {"canvases": [30]}


async def test_nollie_target_uses_standby_brightness_state() -> None:
    controller = FakeController(ControllerId("Nollie16", "ABC"), [30, 80])
    target = NollieLightingTarget(controller)

    state = await target.snapshot()
    assert target.identity == TargetIdentity("nollie", "Nollie16:ABC")
    assert state == {"canvases": [30, 80]}

    await target.blackout(state)
    assert controller.brightness == [0, 0]

    await target.restore(state)
    assert controller.brightness == [30, 80]


async def test_nollie_target_translates_read_value_error() -> None:
    controller = ValueErrorController("Nollie16", "ABC", [30], fail_read=True)
    target = NollieLightingTarget(controller)

    with pytest.raises(LightingError) as excinfo:
        await target.snapshot()

    assert str(excinfo.value) == "bad controller read"
    assert isinstance(excinfo.value.__cause__, ValueError)


async def test_nollie_target_translates_write_value_error() -> None:
    controller = ValueErrorController("Nollie16", "ABC", [30], fail_write=True)
    target = NollieLightingTarget(controller)

    with pytest.raises(LightingError) as excinfo:
        await target.restore({"canvases": [30]})

    assert str(excinfo.value) == "bad controller write"
    assert isinstance(excinfo.value.__cause__, ValueError)


@pytest.mark.parametrize(
    "canvases",
    [
        [],
        [True],
        [30.5],
        ["30"],
        [-1],
        [101],
    ],
)
async def test_nollie_target_rejects_malformed_canvas_state(canvases: list[object]) -> None:
    controller = FakeController(ControllerId("Nollie16", "ABC"), [30])
    target = NollieLightingTarget(controller)

    with pytest.raises(LightingError):
        await target.restore({"canvases": canvases})
