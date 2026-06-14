from __future__ import annotations

import logging
from collections.abc import Iterable
from copy import deepcopy

from .domain import ServiceState
from .lighting import BlackoutEligibility, LightingError, LightingSnapshot, LightingTarget
from .protocol import NollieControllerProtocol, NollieLightingTarget
from .storage import StateStore

log = logging.getLogger(__name__)


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
        targets: Iterable[LightingTarget | NollieControllerProtocol],
    ) -> None:
        self.state = ServiceState.DIMMING
        dimmed_any = False
        for item in targets:
            target = self._lighting_target(item)
            key = target.identity.key
            existing = self.snapshots.get(key)
            try:
                if existing is not None and existing.pending_restore:
                    state = deepcopy(existing.state)
                else:
                    state = deepcopy(await target.snapshot())
                    if (
                        isinstance(target, BlackoutEligibility)
                        and not target.should_blackout(state)
                    ):
                        continue
                    self.snapshots[key] = LightingSnapshot(
                        target.identity,
                        deepcopy(state),
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
                await target.blackout(deepcopy(state))
                dimmed_any = True
            except (LightingError, OSError) as exc:
                log.warning("Could not dim %s: %s", key, exc)
        self.state = ServiceState.DIMMED if dimmed_any else ServiceState.ACTIVE

    async def restore(
        self,
        targets: Iterable[LightingTarget | NollieControllerProtocol],
    ) -> None:
        self.state = ServiceState.RESTORING
        lighting_targets = (self._lighting_target(item) for item in targets)
        by_key = {target.identity.key: target for target in lighting_targets}
        for key, snapshot in list(self.snapshots.items()):
            if not snapshot.pending_restore or key not in by_key:
                continue
            try:
                await by_key[key].restore(deepcopy(snapshot.state))
                self.snapshots[key] = LightingSnapshot(
                    snapshot.identity,
                    deepcopy(snapshot.state),
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

    def release(
        self,
        targets: Iterable[LightingTarget | NollieControllerProtocol],
    ) -> None:
        keys = {
            self._lighting_target(target).identity.key
            for target in targets
        }
        removed = {
            key: self.snapshots.pop(key)
            for key in keys
            if key in self.snapshots
        }
        if not removed:
            return
        try:
            self.store.save_snapshots(self.snapshots)
        except (LightingError, OSError) as exc:
            self.snapshots.update(removed)
            log.warning("Could not release lighting ownership: %s", exc)

    @staticmethod
    def _lighting_target(
        item: LightingTarget | NollieControllerProtocol,
    ) -> LightingTarget:
        if isinstance(item, LightingTarget):
            return item
        if isinstance(item, NollieControllerProtocol):
            return NollieLightingTarget(item)
        raise TypeError("unsupported lighting target")


BrightnessService = LightingService
