from __future__ import annotations

import json
import os
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

from .domain import AppSettings, BrightnessSnapshot


class StateStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.state_path = data_dir / "state.json"
        self.settings_path = data_dir / "settings.json"

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
        payload = {"version": 1, "snapshots": {k: v.to_dict() for k, v in snapshots.items()}}
        self._atomic_write(self.state_path, payload)

    def load_settings(self) -> AppSettings:
        if not self.settings_path.exists():
            return AppSettings()
        try:
            payload = json.loads(self.settings_path.read_text(encoding="utf-8"))
            return AppSettings(
                idle_seconds=float(payload.get("idle_seconds", 30)),
                axis_dead_zone=float(payload.get("axis_dead_zone", 0.15)),
                axis_change_threshold=float(payload.get("axis_change_threshold", 0.1)),
                enabled=bool(payload.get("enabled", True)),
                autostart=bool(payload.get("autostart", True)),
            )
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return AppSettings()

    def save_settings(self, settings: AppSettings) -> None:
        self._atomic_write(
            self.settings_path,
            {
                "version": 1,
                "idle_seconds": settings.idle_seconds,
                "axis_dead_zone": settings.axis_dead_zone,
                "axis_change_threshold": settings.axis_change_threshold,
                "enabled": settings.enabled,
                "autostart": settings.autostart,
            },
        )

    def _atomic_write(self, path: Path, payload: object) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
