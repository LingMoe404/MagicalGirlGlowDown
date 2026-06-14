from __future__ import annotations

import json
from pathlib import Path

from nollie_rgb_idle.domain import AppSettings
from nollie_rgb_idle.lighting import LightingSnapshot, TargetIdentity
from nollie_rgb_idle.storage import StateStore


def test_store_round_trips_version_two_opaque_snapshots(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    snapshots = {
        "nollie:Nollie16:ABC": LightingSnapshot(
            TargetIdentity("nollie", "Nollie16:ABC"),
            {"canvases": [30, 80]},
            True,
        ),
        "gigabyte:board": LightingSnapshot(
            TargetIdentity("gigabyte", "board"),
            {"schema": 1, "zones": [{"id": "logo", "brightness": 75}]},
            False,
        ),
    }

    store.save_snapshots(snapshots)

    assert store.load_snapshots() == snapshots
    payload = json.loads(store.state_path.read_text(encoding="utf-8"))
    assert payload["version"] == 2


def test_loads_version_one_brightness_snapshot_and_next_save_emits_v2(
    tmp_path: Path,
) -> None:
    store = StateStore(tmp_path)
    store.state_path.write_text(
        '{"version":1,"snapshots":{"Nollie16:A":{"model":"Nollie16",'
        '"serial":"A","canvases":[30],"pending_restore":true}}}',
        encoding="utf-8",
    )

    loaded = store.load_snapshots()

    assert loaded == {
        "nollie:Nollie16:A": LightingSnapshot(
            TargetIdentity("nollie", "Nollie16:A"),
            {"canvases": [30]},
            True,
        )
    }

    store.save_snapshots(loaded)

    payload = json.loads(store.state_path.read_text(encoding="utf-8"))
    assert payload["version"] == 2
    assert payload["snapshots"]["nollie:Nollie16:A"] == {
        "backend": "nollie",
        "device": "Nollie16:A",
        "state": {"canvases": [30]},
        "pending_restore": True,
    }


def test_corrupt_state_is_quarantined(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    store.state_path.parent.mkdir(parents=True, exist_ok=True)
    store.state_path.write_text("{broken", encoding="utf-8")

    assert store.load_snapshots() == {}
    assert list(tmp_path.glob("state.corrupt-*.json"))


def test_store_round_trips_settings(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    settings = AppSettings(idle_seconds=45, autostart=False)
    store.save_settings(settings)

    assert store.load_settings() == settings
