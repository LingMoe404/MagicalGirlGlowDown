from __future__ import annotations

import json
import os
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

from .domain import BrightnessSnapshot


class StateStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.state_path = data_dir / "state.json"

    def load_snapshots(self) -> dict[str, BrightnessSnapshot]:
        if not self.state_path.exists():
            return {}
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            return {
                key: BrightnessSnapshot.from_dict(item)
                for key, item in payload.get("snapshots", {}).items()
            }
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            quarantine = self.data_dir / f"state.corrupt-{stamp}.json"
            with suppress(OSError):
                os.replace(self.state_path, quarantine)
            return {}

    def save_snapshots(self, snapshots: dict[str, BrightnessSnapshot]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(".tmp")
        payload = {"version": 1, "snapshots": {k: v.to_dict() for k, v in snapshots.items()}}
        temporary.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.state_path)
