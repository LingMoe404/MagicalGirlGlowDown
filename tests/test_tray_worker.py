from magical_girl_glow_down.lighting import LightingSnapshot, TargetIdentity
from magical_girl_glow_down.service import LightingService
from magical_girl_glow_down.storage import StateStore
from magical_girl_glow_down.worker import WorkerPolicy
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


async def test_gcc_ownership_preserves_pending_restore_snapshot(tmp_path) -> None:
    service = LightingService(StateStore(tmp_path))
    service.snapshots["gigabyte:board"] = LightingSnapshot(
        TargetIdentity("gigabyte", "board"),
        {"zones": [{"id": "logo", "brightness": 80}]},
        pending_restore=True,
    )
    service.store.save_snapshots(service.snapshots)
    policy = WorkerPolicy(service)

    await policy.tick([], idle=True, gcc_running=True)

    assert "gigabyte:board" in service.snapshots


async def test_worker_run_loop_throttling_and_close(tmp_path, monkeypatch) -> None:
    from unittest.mock import MagicMock

    from magical_girl_glow_down.tray import StatusBridge, Worker
    from magical_girl_glow_down.windows_input import GameControllerMonitor

    class FakeGigabyteLightingTarget(FakeLightingTarget):
        def __init__(self, backend: str, device: str, state: dict[str, object]) -> None:
            super().__init__(backend, device, state)
            self.close_calls = 0

        async def close(self) -> None:
            self.close_calls += 1

    # Mocks
    mock_original_running = MagicMock(return_value=False)
    mock_gcc_running = MagicMock(return_value=False)
    mock_discover = MagicMock(return_value=[])

    monkeypatch.setattr(
        "magical_girl_glow_down.tray.is_original_app_running",
        mock_original_running,
    )
    monkeypatch.setattr("magical_girl_glow_down.tray.is_gcc_running", mock_gcc_running)
    monkeypatch.setattr("magical_girl_glow_down.tray.discover_controllers", mock_discover)

    # Mock time to step forward manually
    time_val = 100.0
    def mock_monotonic() -> float:
        return time_val
    monkeypatch.setattr("time.monotonic", mock_monotonic)

    # Mock gigabyte target and discovery
    mock_gigabyte_target = FakeGigabyteLightingTarget(
        "gigabyte",
        "board",
        {"zones": [{"id": "logo", "brightness": 80}]},
    )

    # We will instantiate Worker
    monitor = MagicMock(spec=GameControllerMonitor)
    monitor.last_activity = 0.0
    bridge = MagicMock(spec=StatusBridge)

    worker = Worker(
        idle_seconds=30.0,
        data_dir=tmp_path,
        monitor=monitor,
        bridge=bridge,
    )

    # Mock _discover_gigabyte_target
    async def mock_discover_gigabyte() -> FakeGigabyteLightingTarget:
        return mock_gigabyte_target

    worker._discover_gigabyte_target = mock_discover_gigabyte  # type: ignore

    step = 0

    # We can patch asyncio.sleep to check progress and stop/advance time
    async def mock_sleep(delay: float) -> None:
        nonlocal step, time_val
        step += 1
        if step == 1:
            time_val = 101.0
        elif step == 2:
            time_val = 103.0
            mock_gcc_running.return_value = True
        elif step == 3:
            worker.stop_event.set()

    monkeypatch.setattr("asyncio.sleep", mock_sleep)

    # Run the worker's async _run
    await worker._run()

    # Total checks to is_gcc_running and is_original_app_running should be exactly 2
    assert mock_gcc_running.call_count == 2
    assert mock_original_running.call_count == 2

    # gigabyte_target should have been closed when gcc_running became True
    assert mock_gigabyte_target.close_calls == 1


async def test_worker_run_loop_finally_closes_gigabyte(tmp_path, monkeypatch) -> None:
    from unittest.mock import MagicMock

    from magical_girl_glow_down.tray import StatusBridge, Worker
    from magical_girl_glow_down.windows_input import GameControllerMonitor

    class FakeGigabyteLightingTarget(FakeLightingTarget):
        def __init__(self, backend: str, device: str, state: dict[str, object]) -> None:
            super().__init__(backend, device, state)
            self.close_calls = 0

        async def close(self) -> None:
            self.close_calls += 1

    # Mocks
    mock_original_running = MagicMock(return_value=False)
    mock_gcc_running = MagicMock(return_value=False)
    mock_discover = MagicMock(return_value=[])

    monkeypatch.setattr(
        "magical_girl_glow_down.tray.is_original_app_running",
        mock_original_running,
    )
    monkeypatch.setattr("magical_girl_glow_down.tray.is_gcc_running", mock_gcc_running)
    monkeypatch.setattr("magical_girl_glow_down.tray.discover_controllers", mock_discover)

    mock_gigabyte_target = FakeGigabyteLightingTarget(
        "gigabyte",
        "board",
        {"zones": [{"id": "logo", "brightness": 80}]},
    )

    monitor = MagicMock(spec=GameControllerMonitor)
    monitor.last_activity = 0.0
    bridge = MagicMock(spec=StatusBridge)

    worker = Worker(
        idle_seconds=30.0,
        data_dir=tmp_path,
        monitor=monitor,
        bridge=bridge,
    )

    async def mock_discover_gigabyte() -> FakeGigabyteLightingTarget:
        return mock_gigabyte_target

    worker._discover_gigabyte_target = mock_discover_gigabyte  # type: ignore

    async def mock_sleep(delay: float) -> None:
        worker.stop_event.set()

    monkeypatch.setattr("asyncio.sleep", mock_sleep)

    await worker._run()

    # gigabyte_target should have been closed in the finally block
    assert mock_gigabyte_target.close_calls == 1


from copy import deepcopy

from magical_girl_glow_down.lighting import LightingError
from magical_girl_glow_down.tray import StatusBridge, Worker
from magical_girl_glow_down.windows_input import GameControllerMonitor
from tests.fakes import FakeLightingTarget


class TransitionGigabyteTarget(FakeLightingTarget):
    def __init__(self) -> None:
        super().__init__(
            "gigabyte",
            "board",
            {"zones": [{"id": "logo", "brightness": 80}]},
        )
        self.reject_restore = False
        self.close_calls = 0

    async def restore(self, snapshot: dict[str, object]) -> None:
        self.restore_calls += 1
        if self.reject_restore:
            raise LightingError("gcc_running")
        self.state = deepcopy(snapshot)

    async def close(self) -> None:
        self.close_calls += 1


def make_transition_worker(tmp_path) -> Worker:
    return Worker(
        idle_seconds=30.0,
        data_dir=tmp_path,
        monitor=GameControllerMonitor(_xinput=None),
        bridge=StatusBridge(),
        state_dir=tmp_path,
    )


async def test_gcc_start_does_not_discard_failed_pending_restore(
    tmp_path,
) -> None:
    target = TransitionGigabyteTarget()
    worker = make_transition_worker(tmp_path)
    await worker.service.dim([target])
    target.reject_restore = True

    current, next_scan = await worker._transition_gigabyte_target(
        target,
        gcc_running=True,
        was_gcc_running=False,
        now=10.0,
        next_scan=0.0,
    )

    assert current is None
    assert next_scan == 12.0
    assert target.restore_calls == 1
    assert target.close_calls == 1
    assert worker.service.snapshots["gigabyte:board"].pending_restore is True


async def test_gcc_close_retries_pending_restore_before_new_dim(
    tmp_path,
    monkeypatch,
) -> None:
    target = TransitionGigabyteTarget()
    worker = make_transition_worker(tmp_path)
    await worker.service.dim([target])
    target.reject_restore = True
    await worker._transition_gigabyte_target(
        target,
        gcc_running=True,
        was_gcc_running=False,
        now=10.0,
        next_scan=0.0,
    )
    target.reject_restore = False

    async def discover() -> TransitionGigabyteTarget:
        return target

    monkeypatch.setattr(worker, "_discover_gigabyte_target", discover)
    current, _ = await worker._transition_gigabyte_target(
        None,
        gcc_running=False,
        was_gcc_running=True,
        now=20.0,
        next_scan=12.0,
    )

    assert current is target
    assert target.restore_calls == 2
    assert worker.service.snapshots["gigabyte:board"].pending_restore is False


import threading
import pytest
from magical_girl_glow_down.tray import WorkerController

class RecordingSignal:
    def __init__(self) -> None:
        self.values: list[str] = []

    def emit(self, value: str) -> None:
        self.values.append(value)


class RecordingBridge:
    def __init__(self) -> None:
        self.status_changed = RecordingSignal()
        self.worker_failed = RecordingSignal()

    @property
    def failures(self) -> list[str]:
        return self.worker_failed.values


class FakeThread:
    def __init__(self) -> None:
        self._alive = False
        self.stop_event = threading.Event()

    def start(self) -> None:
        self._alive = True

    def is_alive(self) -> bool:
        return self._alive

    def mark_stopped(self) -> None:
        self._alive = False


def build_failure_worker(tmp_path, bridge: RecordingBridge) -> Worker:
    return Worker(
        idle_seconds=30.0,
        data_dir=tmp_path,
        monitor=GameControllerMonitor(_xinput=None),
        bridge=bridge,
    )


def test_worker_emits_failure_when_async_loop_crashes(tmp_path, monkeypatch) -> None:
    bridge = RecordingBridge()
    worker = build_failure_worker(tmp_path, bridge)

    async def fail() -> None:
        raise RuntimeError("input API failed")

    monkeypatch.setattr(worker, "_run", fail)
    worker.run()

    assert bridge.failures == ["input API failed"]


def test_retry_starts_only_after_failed_worker_stops() -> None:
    controller = WorkerController(lambda: FakeThread())
    first = controller.start()
    with pytest.raises(RuntimeError, match="already running"):
        controller.start()
    first.mark_stopped()
    second = controller.restart()
    assert second is not first



