from __future__ import annotations

import pytest

from nollie_rgb_idle.domain import ControllerId
from nollie_rgb_idle.lighting import LightingSnapshot, TargetIdentity
from nollie_rgb_idle.protocol import NollieLightingTarget

from .fakes import FakeController, FakeLightingTarget


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

    with pytest.raises(ValueError):
        await target.restore({"canvases": canvases})
