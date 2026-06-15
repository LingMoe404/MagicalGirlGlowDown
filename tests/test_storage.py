from __future__ import annotations

import json
from pathlib import Path

from magical_girl_glow_down.domain import AppSettings
from magical_girl_glow_down.lighting import LightingSnapshot, TargetIdentity
from magical_girl_glow_down.storage import StateStore


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


def test_version_two_key_identity_mismatch_is_quarantined(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    store.state_path.write_text(
        '{"version":2,"snapshots":{"nollie:Nollie16:WRONG":{'
        '"backend":"nollie","device":"Nollie16:A",'
        '"state":{"canvases":[30]},"pending_restore":true}}}',
        encoding="utf-8",
    )

    assert store.load_snapshots() == {}
    assert store.state_path.exists()
    assert list(tmp_path.glob("state.corrupt-*.json"))


def test_malformed_v2_entry_is_quarantined_without_losing_valid_entries(
    tmp_path: Path,
) -> None:
    store = StateStore(tmp_path)
    store.state_path.write_text(
        json.dumps(
            {
                "version": 2,
                "snapshots": {
                    "nollie:Nollie16:A": {
                        "backend": "nollie",
                        "device": "Nollie16:A",
                        "state": {"canvases": [30]},
                        "pending_restore": True,
                    },
                    "gigabyte:broken": {
                        "backend": "gigabyte",
                        "device": "different",
                        "state": {"zones": []},
                        "pending_restore": True,
                    },
                },
            }
        ),
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
    assert store.state_path.exists()
    assert list(tmp_path.glob("state.corrupt-*.json"))

    store.save_snapshots(loaded)
    payload = json.loads(store.state_path.read_text(encoding="utf-8"))
    assert list(payload["snapshots"]) == ["nollie:Nollie16:A"]



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


def test_settings_and_recovery_state_use_separate_directories(tmp_path: Path) -> None:
    settings_dir = tmp_path / "user"
    state_dir = tmp_path / "protected"
    store = StateStore(settings_dir, state_dir)

    store.save_settings(AppSettings(idle_seconds=45))
    store.save_snapshots(
        {
            "nollie:Nollie16:A": LightingSnapshot(
                TargetIdentity("nollie", "Nollie16:A"),
                {"canvases": [30]},
                True,
            )
        }
    )

    assert store.settings_path.parent == settings_dir
    assert store.state_path.parent == state_dir


def test_legacy_state_migrates_only_after_protected_save(tmp_path: Path) -> None:
    settings_dir = tmp_path / "user"
    state_dir = tmp_path / "protected"
    legacy = settings_dir / "state.json"
    settings_dir.mkdir()
    legacy.write_text(
        '{"version":2,"snapshots":{"nollie:Nollie16:A":{'
        '"backend":"nollie","device":"Nollie16:A",'
        '"state":{"canvases":[30]},"pending_restore":true}}}',
        encoding="utf-8",
    )
    store = StateStore(settings_dir, state_dir)

    store.migrate_legacy_state()

    assert store.load_snapshots()["nollie:Nollie16:A"].pending_restore
    assert not legacy.exists()
    assert list(settings_dir.glob("state.migrated-*.json"))


def test_corrupt_legacy_state_is_quarantined_and_replaced(tmp_path: Path) -> None:
    settings_dir = tmp_path / "user"
    state_dir = tmp_path / "protected"
    legacy = settings_dir / "state.json"
    settings_dir.mkdir()
    legacy.write_text("{broken", encoding="utf-8")
    store = StateStore(settings_dir, state_dir)

    store.migrate_legacy_state()

    assert store.state_path.exists()
    assert json.loads(store.state_path.read_text(encoding="utf-8")) == {
        "version": 2,
        "snapshots": {},
    }
    assert not legacy.exists()
    assert list(settings_dir.glob("state.corrupt-*.json"))


def test_mixed_corruption_rewrites_valid_entries(tmp_path: Path) -> None:
    store = StateStore(tmp_path, tmp_path)
    store.state_path.write_text(
        json.dumps(
            {
                "version": 2,
                "snapshots": {
                    "nollie:Nollie16:A": {
                        "backend": "nollie",
                        "device": "Nollie16:A",
                        "state": {"canvases": [30]},
                        "pending_restore": True,
                    },
                    "gigabyte:bad": {
                        "backend": "gigabyte",
                        "device": "different",
                        "state": {},
                        "pending_restore": True,
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    first = store.load_snapshots()
    second = StateStore(tmp_path, tmp_path).load_snapshots()

    assert list(first) == ["nollie:Nollie16:A"]
    assert list(second) == ["nollie:Nollie16:A"]
    assert list(tmp_path.glob("state.corrupt-*.json"))

