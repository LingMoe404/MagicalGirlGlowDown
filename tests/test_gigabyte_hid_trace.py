from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from tools.gigabyte_hid_trace import (
    FRIDA_AGENT,
    build_parser,
    normalize_trace_event,
    select_process,
    write_jsonl,
)


@dataclass(frozen=True)
class FakeProcess:
    pid: int
    name: str


def test_normalize_trace_event_keeps_hid_metadata_and_uppercase_hex() -> None:
    event = normalize_trace_event(
        {
            "operation": "write",
            "vendor_id": 0x048D,
            "product_id": 0x8297,
            "device": 0,
            "size": 4,
            "data_hex": "cc200100",
            "result": 1,
        },
        process_id=42,
        process_name="GCC.exe",
        timestamp="2026-06-15T00:00:00Z",
    )

    assert event == {
        "timestamp": "2026-06-15T00:00:00Z",
        "process": {"pid": 42, "name": "GCC.exe"},
        "operation": "write",
        "vendor_id": 0x048D,
        "product_id": 0x8297,
        "device": 0,
        "size": 4,
        "data_hex": "CC200100",
        "result": 1,
    }


def test_normalize_trace_event_rejects_unknown_operations() -> None:
    with pytest.raises(ValueError, match="unsupported trace operation"):
        normalize_trace_event(
            {"operation": "connect"},
            process_id=42,
            process_name="GCC.exe",
            timestamp="2026-06-15T00:00:00Z",
        )


def test_agent_hooks_only_ghid_read_and_write_exports() -> None:
    assert "dllexp_WriteDataToDevice" in FRIDA_AGENT
    assert "dllexp_ReadDataFromDevice" in FRIDA_AGENT
    assert "Interceptor.attach" in FRIDA_AGENT
    assert "Interceptor.replace" not in FRIDA_AGENT
    assert "NativeFunction" not in FRIDA_AGENT


def test_select_process_matches_name_case_insensitively() -> None:
    process = select_process(
        [FakeProcess(7, "gcc.exe"), FakeProcess(8, "Other.exe")],
        process_name="GCC.exe",
    )

    assert process.pid == 7


def test_select_process_prefers_requested_pid() -> None:
    process = select_process(
        [FakeProcess(7, "GCC.exe"), FakeProcess(8, "GCC.exe")],
        process_name="GCC.exe",
        process_id=8,
    )

    assert process.pid == 8


def test_write_jsonl_appends_one_compact_record(tmp_path: Path) -> None:
    output = tmp_path / "trace.jsonl"

    write_jsonl(output, {"operation": "write", "data_hex": "CC20"})
    write_jsonl(output, {"operation": "read", "data_hex": "CC21"})

    records = [
        json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()
    ]
    assert records == [
        {"operation": "write", "data_hex": "CC20"},
        {"operation": "read", "data_hex": "CC21"},
    ]


def test_parser_accepts_pid_and_bounded_capture_duration() -> None:
    args = build_parser().parse_args(
        ["--pid", "42", "--wait-seconds", "15", "--duration-seconds", "3"]
    )

    assert args.pid == 42
    assert args.process == "GCC.exe"
    assert args.wait_seconds == 15
    assert args.duration_seconds == 3


@pytest.mark.parametrize(
    ("argument", "value"),
    [
        ("--wait-seconds", "-1"),
        ("--duration-seconds", "-1"),
    ],
)
def test_parser_rejects_negative_durations(argument: str, value: str) -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args([argument, value])
