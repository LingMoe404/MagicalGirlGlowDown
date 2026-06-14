from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from .lighting import TargetIdentity
from .service import LightingService
from .storage import StateStore


@dataclass
class SimulatedLightingTarget:
    identity: TargetIdentity
    values: list[int]

    async def snapshot(self) -> dict[str, object]:
        return {"canvases": deepcopy(self.values)}

    async def blackout(self, snapshot: dict[str, object]) -> None:
        canvases = self._canvases(snapshot)
        self.values[:] = [0 for _ in canvases]

    async def restore(self, snapshot: dict[str, object]) -> None:
        self.values[:] = self._canvases(snapshot)

    @staticmethod
    def _canvases(snapshot: dict[str, object]) -> list[int]:
        canvases = snapshot.get("canvases")
        if not isinstance(canvases, list) or any(type(value) is not int for value in canvases):
            raise ValueError("invalid simulated lighting snapshot")
        return canvases


@dataclass(frozen=True, slots=True)
class SimulationResult:
    dimmed: tuple[tuple[int, ...], ...]
    restored: tuple[tuple[int, ...], ...]


async def run_simulation(
    data_dir: Path,
    idle_seconds: float,
    cycles: int,
    sleep: Callable[[float], Awaitable[object] | None] | None = None,
) -> SimulationResult:
    targets = [
        SimulatedLightingTarget(TargetIdentity("nollie", "Nollie16:SIM-A"), [30, 80]),
        SimulatedLightingTarget(TargetIdentity("nollie", "Nollie8:SIM-B"), [55]),
    ]
    service = LightingService(StateStore(data_dir))
    sleeper = sleep or asyncio.sleep
    dimmed: tuple[tuple[int, ...], ...] = ()
    restored: tuple[tuple[int, ...], ...] = ()
    for _ in range(cycles):
        result = sleeper(idle_seconds)
        if result is not None:
            await result
        await service.dim(targets)
        dimmed = tuple(tuple(item.values) for item in targets)
        await service.restore(targets)
        restored = tuple(tuple(item.values) for item in targets)
    return SimulationResult(dimmed, restored)
