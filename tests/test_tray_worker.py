from nollie_rgb_idle.lighting import LightingSnapshot, TargetIdentity
from nollie_rgb_idle.service import LightingService
from nollie_rgb_idle.storage import StateStore
from nollie_rgb_idle.worker import WorkerPolicy
from tests.fakes import FakeLightingTarget


async def test_gcc_start_restores_and_pauses_only_gigabyte(tmp_path) -> None:
    nollie = FakeLightingTarget("nollie", "A", {"canvases": [30]})
    gigabyte = FakeLightingTarget(
        "gigabyte",
        "board",
        {"zones": [{"id": "logo", "brightness": 80}]},
    )
    policy = WorkerPolicy(LightingService(StateStore(tmp_path)))

    await policy.tick([nollie, gigabyte], idle=True)
    await policy.tick([nollie, gigabyte], idle=True, gcc_running=True)

    assert gigabyte.restore_calls == 1
    assert gigabyte.state["zones"][0]["brightness"] == 80
    assert nollie.restore_calls == 0
    assert nollie.state == {"canvases": [0]}


async def test_nolliergb_start_restores_and_pauses_only_nollie(tmp_path) -> None:
    nollie = FakeLightingTarget("nollie", "A", {"canvases": [30]})
    gigabyte = FakeLightingTarget(
        "gigabyte",
        "board",
        {"zones": [{"id": "logo", "brightness": 80}]},
    )
    policy = WorkerPolicy(LightingService(StateStore(tmp_path)))

    await policy.tick([nollie, gigabyte], idle=True)
    await policy.tick([nollie, gigabyte], idle=True, nolliergb_running=True)

    assert nollie.restore_calls == 1
    assert nollie.state == {"canvases": [30]}
    assert gigabyte.restore_calls == 0


async def test_activity_restores_all_backends(tmp_path) -> None:
    targets = [
        FakeLightingTarget("nollie", "A", {"canvases": [30]}),
        FakeLightingTarget(
            "gigabyte",
            "board",
            {"zones": [{"id": "logo", "brightness": 80}]},
        ),
    ]
    policy = WorkerPolicy(LightingService(StateStore(tmp_path)))

    await policy.tick(targets, idle=True)
    await policy.tick(targets, idle=False)

    assert [target.restore_calls for target in targets] == [1, 1]


async def test_gcc_ownership_discards_stale_pending_snapshot(tmp_path) -> None:
    gigabyte = FakeLightingTarget(
        "gigabyte",
        "board",
        {"zones": [{"id": "logo", "brightness": 80}]},
    )
    service = LightingService(StateStore(tmp_path))
    policy = WorkerPolicy(service)

    await policy.tick([gigabyte], idle=True)
    await policy.tick([gigabyte], idle=True, gcc_running=True)

    assert "gigabyte:board" not in service.snapshots


async def test_gcc_ownership_discards_orphaned_persisted_snapshot(tmp_path) -> None:
    service = LightingService(StateStore(tmp_path))
    service.snapshots["gigabyte:board"] = LightingSnapshot(
        TargetIdentity("gigabyte", "board"),
        {"zones": [{"id": "logo", "brightness": 80}]},
        pending_restore=True,
    )
    service.store.save_snapshots(service.snapshots)
    policy = WorkerPolicy(service)

    await policy.tick([], idle=True, gcc_running=True)

    assert "gigabyte:board" not in service.snapshots
