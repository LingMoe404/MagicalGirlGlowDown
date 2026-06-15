from magical_girl_glow_down.windows_input import (
    RAWHID_PREFIX,
    RAWINPUTHEADER,
    GameControllerMonitor,
    parse_raw_hid_buffer,
    state_has_activity,
)


def test_controller_buttons_and_large_axis_changes_count_as_activity() -> None:
    assert state_has_activity(None, (0, 0, 0), dead_zone=1000)
    assert state_has_activity((0, 0, 0), (1, 0, 0), dead_zone=1000)
    assert state_has_activity((1, 0, 0), (1, 500, 0), dead_zone=1000) is False
    assert state_has_activity((1, 0, 0), (1, 1500, 0), dead_zone=1000)


def test_raw_input_records_only_changed_reports(monkeypatch) -> None:
    times = iter([10.0, 20.0])
    monkeypatch.setattr("time.monotonic", lambda: next(times))
    monitor = GameControllerMonitor(_xinput=None)

    assert monitor.record_raw_report(7, b"\x01\x02")
    assert monitor.last_activity == 10.0
    assert not monitor.record_raw_report(7, b"\x01\x02")
    assert monitor.last_activity == 10.0
    assert monitor.record_raw_report(7, b"\x01\x03")
    assert monitor.last_activity == 20.0


def test_raw_input_devices_are_cached_independently(monkeypatch) -> None:
    monkeypatch.setattr("time.monotonic", lambda: 10.0)
    monitor = GameControllerMonitor(_xinput=None)

    assert monitor.record_raw_report(7, b"\x01")
    assert monitor.record_raw_report(8, b"\x01")


def test_parse_raw_hid_buffer_returns_device_and_report() -> None:
    header = RAWINPUTHEADER()
    header.dwType = 2
    header.hDevice = 7
    prefix = RAWHID_PREFIX()
    prefix.dwSizeHid = 2
    prefix.dwCount = 1
    raw = bytes(header) + bytes(prefix) + b"\x01\x02"

    assert parse_raw_hid_buffer(raw) == (7, b"\x01\x02")


def test_parse_raw_hid_buffer_rejects_non_hid_input() -> None:
    header = RAWINPUTHEADER()
    header.dwType = 0
    raw = bytes(header) + bytes(RAWHID_PREFIX())

    assert parse_raw_hid_buffer(raw) is None
