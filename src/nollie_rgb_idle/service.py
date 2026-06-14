from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Protocol

from .domain import BrightnessSnapshot, ControllerId, ServiceState
from .storage import StateStore

log = logging.getLogger(__name__)


class Controller(Protocol):
    identity: ControllerId

    async def read_standby_brightness(self) -> tuple[int, ...]: ...

    async def write_standby_brightness(self, values: tuple[int, ...]) -> None: ...


class BrightnessService:
    def __init__(self, store: StateStore) -> None:
        self.store = store
        self.snapshots = store.load_snapshots()
        self.state = ServiceState.ACTIVE

    async def dim(self, controllers: Iterable[Controller]) -> None:
        self.state = ServiceState.DIMMING
        dimmed_any = False
        for controller in controllers:
            key = controller.identity.key
            existing = self.snapshots.get(key)
            try:
                current = await controller.read_standby_brightness()
                if not current:
                    continue
                if existing is None or not existing.pending_restore:
                    if all(value == 0 for value in current):
                        continue
                    self.snapshots[key] = BrightnessSnapshot(
                        controller.identity,
                        current,
                        pending_restore=True,
                    )
                    self.store.save_snapshots(self.snapshots)
                await controller.write_standby_brightness(tuple(0 for _ in current))
                dimmed_any = True
            except OSError as exc:
                log.warning("Could not dim %s: %s", key, exc)
        self.state = ServiceState.DIMMED if dimmed_any else ServiceState.ACTIVE

    async def restore(self, controllers: Iterable[Controller]) -> None:
        self.state = ServiceState.RESTORING
        by_key = {controller.identity.key: controller for controller in controllers}
        for key, snapshot in list(self.snapshots.items()):
            if not snapshot.pending_restore or key not in by_key:
                continue
            try:
                await by_key[key].write_standby_brightness(snapshot.canvases)
            except OSError as exc:
                log.warning("Could not restore %s: %s", key, exc)
                continue
            self.snapshots[key] = BrightnessSnapshot(
                snapshot.controller,
                snapshot.canvases,
                pending_restore=False,
            )
            self.store.save_snapshots(self.snapshots)
        self.state = (
            ServiceState.DIMMED
            if any(item.pending_restore for item in self.snapshots.values())
            else ServiceState.ACTIVE
        )

    def pause(self) -> None:
        self.state = ServiceState.PAUSED
