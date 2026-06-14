from __future__ import annotations

from nollie_rgb_idle.input_monitor import ActivityTracker, AxisFilter


def test_tracker_transitions_after_timeout() -> None:
    tracker = ActivityTracker(idle_seconds=30, now=100)
    assert tracker.is_idle(129) is False
    assert tracker.is_idle(130) is True
    tracker.record_activity(131)
    assert tracker.is_idle(131) is False


def test_axis_filter_ignores_noise_and_detects_motion() -> None:
    axis = AxisFilter(dead_zone=0.15, change_threshold=0.1)
    assert axis.update("pad:lx", 0.02) is False
    assert axis.update("pad:lx", 0.08) is False
    assert axis.update("pad:lx", 0.5) is True
    assert axis.update("pad:lx", 0.53) is False
