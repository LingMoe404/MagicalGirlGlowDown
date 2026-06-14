from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from .domain import ControllerId
from .service import BrightnessService
from .storage import StateStore


@dataclass
class SimulatedController:
    identity: ControllerId
    values: list[int]

    async def read_standby_brightness(self) -> tuple[int, ...]:
        return tuple(self.values)

    async def write_standby_brightness(self, values: tuple[int, ...]) -> None:
        self.values[:] = values


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
    controllers = [
        SimulatedController(ControllerId("Nollie16", "SIM-A"), [30, 80]),
        SimulatedController(ControllerId("Nollie8", "SIM-B"), [55]),
    ]
    service = BrightnessService(StateStore(data_dir))
    sleeper = sleep or asyncio.sleep
    dimmed: tuple[tuple[int, ...], ...] = ()
    restored: tuple[tuple[int, ...], ...] = ()
    for _ in range(cycles):
        result = sleeper(idle_seconds)
        if result is not None:
            await result
        await service.dim(controllers)
        dimmed = tuple(tuple(item.values) for item in controllers)
        await service.restore(controllers)
        restored = tuple(tuple(item.values) for item in controllers)
    return SimulationResult(dimmed, restored)
