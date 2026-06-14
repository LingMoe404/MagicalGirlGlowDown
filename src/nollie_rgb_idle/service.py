from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Protocol

from .domain import ControllerId, ServiceState
from .lighting import LightingError, LightingSnapshot, LightingTarget, TargetIdentity
from .storage import StateStore

log = logging.getLogger(__name__)


class BrightnessController(Protocol):
    identity: ControllerId

    async def read_standby_brightness(self) -> tuple[int, ...]: ...

    async def write_standby_brightness(self, values: tuple[int, ...]) -> None: ...


@dataclass(slots=True)
class _BrightnessTarget:
    controller: BrightnessController
    identity: TargetIdentity = field(init=False)

    def __post_init__(self) -> None:
        self.identity = TargetIdentity("nollie", self.controller.identity.key)

    async def snapshot(self) -> dict[str, object]:
        values = await self.controller.read_standby_brightness()
        return {"canvases": list(values)}

    async def blackout(self, snapshot: dict[str, object]) -> None:
        canvases = self._canvases(snapshot)
        await self.controller.write_standby_brightness(tuple(0 for _ in canvases))

    async def restore(self, snapshot: dict[str, object]) -> None:
        await self.controller.write_standby_brightness(self._canvases(snapshot))

    @staticmethod
    def _canvases(snapshot: dict[str, object]) -> tuple[int, ...]:
        canvases = snapshot.get("canvases")
        if not isinstance(canvases, list) or any(type(value) is not int for value in canvases):
            raise LightingError("invalid Nollie brightness snapshot")
        return tuple(canvases)


class LightingService:
    def __init__(self, store: StateStore) -> None:
        self.store = store
        self.snapshots = store.load_snapshots()
        self.state = ServiceState.ACTIVE

    @property
    def has_pending_restore(self) -> bool:
        return any(item.pending_restore for item in self.snapshots.values())

    async def dim(
        self,
        targets: Iterable[LightingTarget | BrightnessController],
    ) -> None:
        self.state = ServiceState.DIMMING
        dimmed_any = False
        for item in targets:
            target = self._lighting_target(item)
            key = target.identity.key
            existing = self.snapshots.get(key)
            try:
                if existing is not None and existing.pending_restore:
                    state = existing.state
                else:
                    state = await target.snapshot()
                    self.snapshots[key] = LightingSnapshot(
                        target.identity,
                        state,
                        pending_restore=True,
                    )
                    try:
                        self.store.save_snapshots(self.snapshots)
                    except (LightingError, OSError):
                        if existing is None:
                            del self.snapshots[key]
                        else:
                            self.snapshots[key] = existing
                        raise
                await target.blackout(state)
                dimmed_any = True
            except (LightingError, OSError) as exc:
                log.warning("Could not dim %s: %s", key, exc)
        self.state = ServiceState.DIMMED if dimmed_any else ServiceState.ACTIVE

    async def restore(
        self,
        targets: Iterable[LightingTarget | BrightnessController],
    ) -> None:
        self.state = ServiceState.RESTORING
        lighting_targets = (self._lighting_target(item) for item in targets)
        by_key = {target.identity.key: target for target in lighting_targets}
        for key, snapshot in list(self.snapshots.items()):
            if not snapshot.pending_restore or key not in by_key:
                continue
            try:
                await by_key[key].restore(snapshot.state)
                self.snapshots[key] = LightingSnapshot(
                    snapshot.identity,
                    snapshot.state,
                    pending_restore=False,
                )
                try:
                    self.store.save_snapshots(self.snapshots)
                except (LightingError, OSError):
                    self.snapshots[key] = snapshot
                    raise
            except (LightingError, OSError) as exc:
                log.warning("Could not restore %s: %s", key, exc)
        self.state = (
            ServiceState.DIMMED
            if any(item.pending_restore for item in self.snapshots.values())
            else ServiceState.ACTIVE
        )

    def pause(self) -> None:
        self.state = ServiceState.PAUSED

    @staticmethod
    def _lighting_target(
        item: LightingTarget | BrightnessController,
    ) -> LightingTarget:
        if all(hasattr(item, name) for name in ("snapshot", "blackout", "restore")):
            return item  # type: ignore[return-value]
        return _BrightnessTarget(item)  # type: ignore[arg-type]


BrightnessService = LightingService
