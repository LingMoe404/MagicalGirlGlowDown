from magical_girl_glow_down.windows_input import (
    RAWHID_PREFIX,
    RAWINPUTHEADER,
    UINT_ERROR,
    GameControllerMonitor,
    parse_raw_hid_buffer,
    read_raw_input_report,
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


def test_read_raw_input_report_handles_api_failure(monkeypatch) -> None:
    def fake_get_raw_input_data(*args):
        return UINT_ERROR

    monkeypatch.setattr(
        "ctypes.windll.user32.GetRawInputData",
        fake_get_raw_input_data,
        raising=False,
    )

    assert read_raw_input_report(123) is None
    assert fake_get_raw_input_data.restype is not None
    assert fake_get_raw_input_data.argtypes


def test_read_raw_input_report_rejects_invalid_report_size(monkeypatch) -> None:
    calls: list[object] = []

    def fake_get_raw_input_data(handle, command, buffer, size_ptr, header_size):
        calls.append(buffer is None)
        size_ptr._obj.value = 1
        return 1

    monkeypatch.setattr(
        "ctypes.windll.user32.GetRawInputData",
        fake_get_raw_input_data,
        raising=False,
    )

    assert read_raw_input_report(123) is None
    assert calls == [True, False]
    assert fake_get_raw_input_data.argtypes
