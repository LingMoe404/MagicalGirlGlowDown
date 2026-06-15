from __future__ import annotations

from collections.abc import Iterable

from .lighting import LightingTarget
from .service import LightingService


class WorkerPolicy:
    def __init__(self, service: LightingService) -> None:
        self.service = service

    async def tick(
        self,
        targets: Iterable[LightingTarget],
        *,
        idle: bool,
        gcc_running: bool = False,
        nolliergb_running: bool = False,
        manually_paused: bool = False,
        restore_requested: bool = False,
    ) -> str:
        available = list(targets)
        if manually_paused or restore_requested or not idle:
            await self.service.restore(available)
            return "Paused" if manually_paused else "Active"

        blocked_backends: set[str] = set()
        if gcc_running:
            blocked_backends.add("gigabyte")
        if nolliergb_running:
            blocked_backends.add("nollie")

        blocked = [target for target in available if target.identity.backend in blocked_backends]
        allowed = [
            target for target in available if target.identity.backend not in blocked_backends
        ]
        if blocked:
            await self.service.restore(blocked)
        for backend in blocked_backends:
            self.service.release_backend_if_recovered(backend)
        if allowed:
            await self.service.dim(allowed)

        if gcc_running and nolliergb_running:
            return "Paused: GCC and NollieRGB are open"
        if gcc_running:
            return "Gigabyte paused: GCC is open"
        if nolliergb_running:
            return "Nollie paused: NollieRGB is open"
        return "Dimmed" if available else "Waiting for lighting devices"
