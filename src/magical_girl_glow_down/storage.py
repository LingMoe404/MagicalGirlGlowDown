from __future__ import annotations

import json
import logging
import os
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .domain import AppSettings, BrightnessSnapshot
from .lighting import LightingError, LightingSnapshot, TargetIdentity

log = logging.getLogger(__name__)


class StateStore:
    def __init__(self, settings_dir: Path, state_dir: Path | None = None) -> None:
        self.settings_dir = settings_dir
        self.state_dir = state_dir or settings_dir
        self.data_dir = self.settings_dir
        self.state_path = self.state_dir / "state.json"
        self.settings_path = self.settings_dir / "settings.json"
        self.legacy_state_path = self.settings_dir / "state.json"

    def migrate_legacy_state(self) -> None:
        if self.state_path.exists() or self.legacy_state_path == self.state_path:
            return
        if not self.legacy_state_path.exists():
            return
        legacy_store = StateStore(self.settings_dir, self.settings_dir)
        snapshots = legacy_store.load_snapshots()
        self.save_snapshots(snapshots)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        migrated = self.settings_dir / f"state.migrated-{stamp}.json"
        os.replace(self.legacy_state_path, migrated)

    def load_snapshots(self) -> dict[str, LightingSnapshot]:
        if not self.state_path.exists():
            return {}
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            version = int(payload.get("version", 1))
            snapshots = payload.get("snapshots", {})
            if not isinstance(snapshots, dict):
                raise ValueError("snapshots must be a dictionary")
            if version == 1:
                return self._migrate_v1_snapshots(snapshots)
            if version == 2:
                loaded, rejected = self._load_v2_snapshots(snapshots)
                if rejected:
                    for key, reason in rejected.items():
                        log.warning("Discarding invalid recovery snapshot %s: %s", key, reason)
                    self._quarantine_state()
                    self.save_snapshots(loaded)
                return loaded
            raise ValueError(f"unsupported state version: {version}")
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            self._quarantine_state()
            return {}

    def save_snapshots(self, snapshots: dict[str, LightingSnapshot]) -> None:
        payload = {"version": 2, "snapshots": {k: v.to_dict() for k, v in snapshots.items()}}
        self._atomic_write(self.state_path, payload)

    @staticmethod
    def _migrate_v1_snapshots(
        snapshots: dict[str, Any],
    ) -> dict[str, LightingSnapshot]:
        migrated: dict[str, LightingSnapshot] = {}
        for item in snapshots.values():
            legacy = BrightnessSnapshot.from_dict(item)
            identity = TargetIdentity("nollie", legacy.controller.key)
            migrated[identity.key] = LightingSnapshot(
                identity=identity,
                state={"canvases": list(legacy.canvases)},
                pending_restore=legacy.pending_restore,
            )
        return migrated

    @staticmethod
    def _load_v2_snapshots(
        snapshots: dict[str, Any],
    ) -> tuple[dict[str, LightingSnapshot], dict[str, str]]:
        loaded: dict[str, LightingSnapshot] = {}
        rejected: dict[str, str] = {}
        for key, item in snapshots.items():
            try:
                if not isinstance(item, dict):
                    raise ValueError("snapshot entry must be a dictionary")
                snapshot = LightingSnapshot.from_dict(item)
                if key != snapshot.identity.key:
                    raise ValueError("snapshot key does not match target identity")
                loaded[key] = snapshot
            except (KeyError, TypeError, ValueError) as exc:
                rejected[str(key)] = str(exc)
        return loaded, rejected

    def _quarantine_state(self) -> None:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        quarantine = self.state_dir / f"state.corrupt-{stamp}.json"
        with suppress(OSError):
            os.replace(self.state_path, quarantine)

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
        try:
            serialized = json.dumps(payload, ensure_ascii=True, indent=2) + "\n"
        except (TypeError, ValueError) as exc:
            raise LightingError("state is not JSON serializable") from exc
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(serialized, encoding="utf-8")
        os.replace(temporary, path)

