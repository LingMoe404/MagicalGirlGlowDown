from __future__ import annotations

import pytest

from magical_girl_glow_down.domain import AppSettings, BrightnessSnapshot, ControllerId


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


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_settings_reject_non_finite_idle_seconds(value: float) -> None:
    with pytest.raises(ValueError, match="idle_seconds must be finite"):
        AppSettings(idle_seconds=value)


@pytest.mark.parametrize("field", ["axis_dead_zone", "axis_change_threshold"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_settings_reject_non_finite_axis_values(field: str, value: float) -> None:
    values = {field: value}
    with pytest.raises(ValueError, match=f"{field} must be finite"):
        AppSettings(**values)

