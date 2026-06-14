from __future__ import annotations

from pathlib import Path

from nollie_rgb_idle.domain import BrightnessSnapshot, ControllerId
from nollie_rgb_idle.storage import StateStore


def test_store_round_trips_snapshots(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    snapshot = BrightnessSnapshot(ControllerId("Nollie16", "ABC"), (30, 80), True)
    store.save_snapshots({snapshot.controller.key: snapshot})
    assert store.load_snapshots() == {snapshot.controller.key: snapshot}


def test_corrupt_state_is_quarantined(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    store.state_path.parent.mkdir(parents=True, exist_ok=True)
    store.state_path.write_text("{broken", encoding="utf-8")
    assert store.load_snapshots() == {}
    assert list(tmp_path.glob("state.corrupt-*.json"))
