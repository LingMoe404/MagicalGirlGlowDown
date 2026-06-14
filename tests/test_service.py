from __future__ import annotations

from nollie_rgb_idle.domain import ControllerId, ServiceState
from nollie_rgb_idle.service import BrightnessService
from nollie_rgb_idle.storage import StateStore
from tests.fakes import FakeController


async def test_dims_and_restores_all_controllers(tmp_path) -> None:
    controllers = [
        FakeController(ControllerId("Nollie16", "A"), [30, 80]),
        FakeController(ControllerId("Nollie8", "B"), [55]),
    ]
    service = BrightnessService(StateStore(tmp_path))
    await service.dim(controllers)
    assert [controller.brightness for controller in controllers] == [[0, 0], [0]]
    assert service.state is ServiceState.DIMMED
    await service.restore(controllers)
    assert [controller.brightness for controller in controllers] == [[30, 80], [55]]
    assert service.state is ServiceState.ACTIVE


async def test_partial_read_failure_does_not_dim_failed_controller(tmp_path) -> None:
    good = FakeController(ControllerId("Nollie16", "A"), [30])
    bad = FakeController(ControllerId("Nollie8", "B"), [60], fail_read=True)
    service = BrightnessService(StateStore(tmp_path))
    await service.dim([good, bad])
    assert good.brightness == [0]
    assert bad.brightness == [60]


async def test_existing_snapshot_is_not_overwritten_by_zero(tmp_path) -> None:
    controller = FakeController(ControllerId("Nollie16", "A"), [30])
    service = BrightnessService(StateStore(tmp_path))
    await service.dim([controller])
    await service.dim([controller])
    await service.restore([controller])
    assert controller.brightness == [30]
