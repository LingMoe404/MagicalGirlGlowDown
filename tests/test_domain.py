from __future__ import annotations

import pytest

from nollie_rgb_idle.domain import AppSettings, BrightnessSnapshot, ControllerId


def test_settings_reject_non_positive_timeout() -> None:
    with pytest.raises(ValueError):
        AppSettings(idle_seconds=0)


def test_snapshot_round_trip() -> None:
    snapshot = BrightnessSnapshot(
        controller=ControllerId("Nollie16", "ABC"),
        canvases=(30, 80),
        pending_restore=True,
    )
    assert BrightnessSnapshot.from_dict(snapshot.to_dict()) == snapshot


def test_snapshot_rejects_invalid_brightness() -> None:
    with pytest.raises(ValueError):
        BrightnessSnapshot(ControllerId("Nollie16", "ABC"), (101,))
