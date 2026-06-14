from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol


class LightingError(Exception):
    """A recoverable target-specific lighting operation failure."""


@dataclass(frozen=True, slots=True)
class TargetIdentity:
    backend: str
    device: str

    @property
    def key(self) -> str:
        return f"{self.backend}:{self.device}"


@dataclass(frozen=True, slots=True)
class LightingSnapshot:
    identity: TargetIdentity
    state: dict[str, object]
    pending_restore: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.identity.backend,
            "device": self.identity.device,
            "state": deepcopy(self.state),
            "pending_restore": self.pending_restore,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> LightingSnapshot:
        state = value["state"]
        if not isinstance(state, dict):
            raise ValueError("lighting snapshot state must be a dictionary")
        return cls(
            identity=TargetIdentity(str(value["backend"]), str(value["device"])),
            state=deepcopy(state),
            pending_restore=bool(value.get("pending_restore", False)),
        )


class LightingTarget(Protocol):
    identity: TargetIdentity

    async def snapshot(self) -> dict[str, object]: ...

    async def blackout(self, snapshot: dict[str, object]) -> None: ...

    async def restore(self, snapshot: dict[str, object]) -> None: ...
