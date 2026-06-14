from __future__ import annotations


class ActivityTracker:
    def __init__(self, idle_seconds: float, now: float) -> None:
        if idle_seconds <= 0:
            raise ValueError("idle_seconds must be positive")
        self.idle_seconds = idle_seconds
        self.last_activity = now

    def record_activity(self, timestamp: float) -> None:
        self.last_activity = max(self.last_activity, timestamp)

    def is_idle(self, timestamp: float) -> bool:
        return timestamp - self.last_activity >= self.idle_seconds


class AxisFilter:
    def __init__(self, dead_zone: float = 0.15, change_threshold: float = 0.1) -> None:
        self.dead_zone = dead_zone
        self.change_threshold = change_threshold
        self._values: dict[str, float] = {}

    def update(self, axis: str, value: float) -> bool:
        previous = self._values.get(axis, 0.0)
        self._values[axis] = value
        if abs(value) <= self.dead_zone:
            return False
        return abs(value - previous) >= self.change_threshold
