from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .lighting import LightingSnapshot, TargetIdentity

__all__ = [
    "AppSettings",
    "BrightnessSnapshot",
    "ControllerId",
    "LightingSnapshot",
    "ServiceState",
    "TargetIdentity",
]


class ServiceState(StrEnum):
    ACTIVE = "active"
    DIMMING = "dimming"
    DIMMED = "dimmed"
    RESTORING = "restoring"
    PAUSED = "paused"


@dataclass(frozen=True, slots=True)
class AppSettings:
    idle_seconds: float = 30.0
    axis_dead_zone: float = 0.15
    axis_change_threshold: float = 0.1
    enabled: bool = True
    autostart: bool = True

    def __post_init__(self) -> None:
        import math

        if not math.isfinite(self.idle_seconds):
            raise ValueError("idle_seconds must be finite")
        if self.idle_seconds <= 0:
            raise ValueError("idle_seconds must be positive")
        for name, value in (
            ("axis_dead_zone", self.axis_dead_zone),
            ("axis_change_threshold", self.axis_change_threshold),
        ):
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")



@dataclass(frozen=True, slots=True)
class ControllerId:
    model: str
    serial: str

    @property
    def key(self) -> str:
        return f"{self.model}:{self.serial}"


@dataclass(frozen=True, slots=True)
class BrightnessSnapshot:
    controller: ControllerId
    canvases: tuple[int, ...]
    pending_restore: bool = False

    def __post_init__(self) -> None:
        if not self.canvases:
            raise ValueError("snapshot must contain at least one canvas")
        if any(value < 0 or value > 100 for value in self.canvases):
            raise ValueError("brightness must be between 0 and 100")

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.controller.model,
            "serial": self.controller.serial,
            "canvases": list(self.canvases),
            "pending_restore": self.pending_restore,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> BrightnessSnapshot:
        return cls(
            controller=ControllerId(str(value["model"]), str(value["serial"])),
            canvases=tuple(int(item) for item in value["canvases"]),
            pending_restore=bool(value.get("pending_restore", False)),
        )
