from __future__ import annotations

from copy import deepcopy

from nollie_rgb_idle.domain import ControllerId, ServiceState
from nollie_rgb_idle.lighting import LightingError, LightingSnapshot, TargetIdentity
from nollie_rgb_idle.protocol import NollieLightingTarget
from nollie_rgb_idle.service import BrightnessService, LightingService
from nollie_rgb_idle.storage import StateStore
from tests.fakes import FakeController, FakeLightingTarget


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


class FailingLightingTarget(FakeLightingTarget):
    def __init__(
        self,
        backend: str,
        device: str,
        state: dict[str, object],
        *,
        fail_snapshot: bool = False,
        fail_blackout: bool = False,
        fail_restore: bool = False,
    ) -> None:
        super().__init__(backend, device, state)
        self.fail_snapshot = fail_snapshot
        self.fail_blackout = fail_blackout
        self.fail_restore = fail_restore

    async def snapshot(self) -> dict[str, object]:
        if self.fail_snapshot:
            raise LightingError("snapshot failed")
        return await super().snapshot()

    async def blackout(self, snapshot: dict[str, object]) -> None:
        if self.fail_blackout:
            raise OSError("blackout failed")
        await super().blackout(snapshot)

    async def restore(self, snapshot: dict[str, object]) -> None:
        if self.fail_restore:
            raise LightingError("restore failed")
        await super().restore(snapshot)


class RecordingStore(StateStore):
    def __init__(self, data_dir) -> None:
        super().__init__(data_dir)
        self.target: FakeLightingTarget | None = None
        self.state_at_save: dict[str, object] | None = None

    def save_snapshots(self, snapshots: dict[str, LightingSnapshot]) -> None:
        if self.target is not None:
            self.state_at_save = deepcopy(self.target.state)
        super().save_snapshots(snapshots)


class FailingStore(StateStore):
    def save_snapshots(self, snapshots: dict[str, LightingSnapshot]) -> None:
        raise OSError("save failed")


class FailOnceStore(StateStore):
    def __init__(self, data_dir) -> None:
        super().__init__(data_dir)
        self.fail_next_save = False

    def save_snapshots(self, snapshots: dict[str, LightingSnapshot]) -> None:
        if self.fail_next_save:
            self.fail_next_save = False
            raise OSError("save failed")
        super().save_snapshots(snapshots)


async def test_dims_and_restores_mixed_targets(tmp_path) -> None:
    targets = [
        FakeLightingTarget("nollie", "A", {"canvases": [30]}),
        FakeLightingTarget(
            "gigabyte",
            "board",
            {"zones": [{"id": "logo", "brightness": 80}]},
        ),
    ]
    service = LightingService(StateStore(tmp_path))

    await service.dim(targets)

    assert targets[0].state == {"canvases": [0]}
    assert targets[1].blackout_calls == 1
    assert service.state is ServiceState.DIMMED

    await service.restore(targets)

    zones = targets[1].state["zones"]
    assert isinstance(zones, list)
    assert zones[0]["brightness"] == 80
    assert service.state is ServiceState.ACTIVE


async def test_dim_persists_each_snapshot_before_blackout(tmp_path) -> None:
    target = FakeLightingTarget("nollie", "A", {"canvases": [30]})
    store = RecordingStore(tmp_path)
    store.target = target
    service = LightingService(store)

    await service.dim([target])

    assert store.state_at_save == {"canvases": [30]}
    assert target.state == {"canvases": [0]}


async def test_existing_pending_snapshot_is_not_overwritten_by_blackout_state(tmp_path) -> None:
    target = FakeLightingTarget("nollie", "A", {"canvases": [30]})
    service = LightingService(StateStore(tmp_path))
    await service.dim([target])

    await service.dim([target])
    await service.restore([target])

    assert target.state == {"canvases": [30]}


async def test_dim_failure_does_not_stop_other_targets(tmp_path) -> None:
    bad = FailingLightingTarget(
        "gigabyte",
        "board",
        {"zones": [{"id": "logo", "brightness": 80}]},
        fail_snapshot=True,
    )
    good = FakeLightingTarget("nollie", "A", {"canvases": [30]})
    service = LightingService(StateStore(tmp_path))

    await service.dim([bad, good])

    assert bad.blackout_calls == 0
    assert good.state == {"canvases": [0]}


async def test_failed_snapshot_persistence_does_not_blackout_or_remain_pending(
    tmp_path,
) -> None:
    target = FakeLightingTarget("nollie", "A", {"canvases": [30]})
    service = LightingService(FailingStore(tmp_path))

    await service.dim([target])

    assert target.blackout_calls == 0
    assert service.snapshots == {}
    assert service.state is ServiceState.ACTIVE


async def test_restore_matches_by_identity_and_retains_failures(tmp_path) -> None:
    failing = FailingLightingTarget(
        "gigabyte",
        "board",
        {"zones": [{"id": "logo", "brightness": 80}]},
        fail_restore=True,
    )
    good = FakeLightingTarget("nollie", "A", {"canvases": [30]})
    service = LightingService(StateStore(tmp_path))
    await service.dim([failing, good])

    replacements = [
        FailingLightingTarget(
            "gigabyte",
            "board",
            {"zones": [{"id": "logo", "brightness": 0}]},
            fail_restore=True,
        ),
        FakeLightingTarget("nollie", "A", {"canvases": [0]}),
    ]
    await service.restore(reversed(replacements))

    assert service.snapshots["gigabyte:board"].pending_restore is True
    assert service.snapshots["nollie:A"].pending_restore is False
    assert replacements[1].state == {"canvases": [30]}
    assert service.state is ServiceState.DIMMED


async def test_restore_save_failure_retains_pending_and_continues(tmp_path) -> None:
    targets = [
        FakeLightingTarget("gigabyte", "board", {"zones": [{"brightness": 80}]}),
        FakeLightingTarget("nollie", "A", {"canvases": [30]}),
    ]
    store = FailOnceStore(tmp_path)
    service = LightingService(store)
    await service.dim(targets)
    store.fail_next_save = True

    await service.restore(targets)

    assert service.snapshots["gigabyte:board"].pending_restore is True
    assert service.snapshots["nollie:A"].pending_restore is False
    assert targets[1].state == {"canvases": [30]}
    assert service.state is ServiceState.DIMMED


async def test_malformed_nollie_restore_does_not_stop_later_target(tmp_path) -> None:
    store = StateStore(tmp_path)
    snapshots = {
        "nollie:Nollie16:A": LightingSnapshot(
            TargetIdentity("nollie", "Nollie16:A"),
            {"canvases": ["bad"]},
            True,
        ),
        "gigabyte:board": LightingSnapshot(
            TargetIdentity("gigabyte", "board"),
            {"zones": [{"brightness": 80}]},
            True,
        ),
    }
    store.save_snapshots(snapshots)
    service = LightingService(store)
    nollie = NollieLightingTarget(
        FakeController(ControllerId("Nollie16", "A"), [0])
    )
    gigabyte = FakeLightingTarget(
        "gigabyte",
        "board",
        {"zones": [{"brightness": 0}]},
    )

    await service.restore([nollie, gigabyte])

    assert service.snapshots["nollie:Nollie16:A"].pending_restore is True
    assert service.snapshots["gigabyte:board"].pending_restore is False
    assert gigabyte.state == {"zones": [{"brightness": 80}]}
    assert service.state is ServiceState.DIMMED


async def test_value_error_during_nollie_dim_is_translated_and_isolated(tmp_path) -> None:
    bad = NollieLightingTarget(
        ValueErrorController("Nollie16", "A", [30], fail_read=True)
    )
    good_controller = ValueErrorController("Nollie8", "B", [80])
    good = NollieLightingTarget(good_controller)
    service = LightingService(StateStore(tmp_path))

    await service.dim([bad, good])

    assert good_controller.brightness == [0]
    assert service.state is ServiceState.DIMMED


async def test_value_error_during_nollie_restore_is_translated_and_isolated(
    tmp_path,
) -> None:
    store = StateStore(tmp_path)
    snapshots = {
        "nollie:Nollie16:A": LightingSnapshot(
            TargetIdentity("nollie", "Nollie16:A"),
            {"canvases": [30]},
            True,
        ),
        "nollie:Nollie8:B": LightingSnapshot(
            TargetIdentity("nollie", "Nollie8:B"),
            {"canvases": [55]},
            True,
        ),
    }
    store.save_snapshots(snapshots)
    service = LightingService(store)
    bad = NollieLightingTarget(
        ValueErrorController("Nollie16", "A", [30], fail_write=True)
    )
    good_controller = ValueErrorController("Nollie8", "B", [0])
    good = NollieLightingTarget(good_controller)

    await service.restore([bad, good])

    assert service.snapshots["nollie:Nollie16:A"].pending_restore is True
    assert service.snapshots["nollie:Nollie8:B"].pending_restore is False
    assert good_controller.brightness == [55]
    assert service.state is ServiceState.DIMMED


async def test_pause_sets_paused_state(tmp_path) -> None:
    service = LightingService(StateStore(tmp_path))

    service.pause()

    assert service.state is ServiceState.PAUSED


async def test_brightness_service_keeps_untouched_tray_controllers_compatible(
    tmp_path,
) -> None:
    controller = FakeController(ControllerId("Nollie16", "A"), [30])
    service = BrightnessService(StateStore(tmp_path))

    await service.dim([controller])
    await service.restore([controller])

    assert controller.brightness == [30]


async def test_all_zero_nollie_target_is_skipped(tmp_path) -> None:
    controller = FakeController(ControllerId("Nollie16", "A"), [0, 0])
    service = LightingService(StateStore(tmp_path))

    await service.dim([NollieLightingTarget(controller)])

    assert controller.brightness == [0, 0]
    assert service.snapshots == {}
    assert service.state is ServiceState.ACTIVE


async def test_empty_legacy_nollie_controller_is_skipped(tmp_path) -> None:
    controller = FakeController(ControllerId("Nollie16", "A"), [])
    service = BrightnessService(StateStore(tmp_path))

    await service.dim([controller])

    assert controller.brightness == []
    assert service.snapshots == {}
    assert service.state is ServiceState.ACTIVE
