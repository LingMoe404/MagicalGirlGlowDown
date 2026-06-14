# /// script
# requires-python = ">=3.12"
# dependencies = ["frida"]
# ///

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

TRACE_OPERATIONS = frozenset({"read", "write"})


class ProcessInfo(Protocol):
    pid: int
    name: str


FRIDA_AGENT = r"""
"use strict";

const MODULE_NAME = "GHidApi.dll";
const EXPORTS = [
    ["write", "dllexp_WriteDataToDevice"],
    ["read", "dllexp_ReadDataFromDevice"],
];
let hooksInstalled = false;

function bufferToHex(pointer, size) {
    if (pointer.isNull() || size <= 0) {
        return "";
    }
    const bytes = new Uint8Array(pointer.readByteArray(size));
    let result = "";
    for (let index = 0; index < bytes.length; index += 1) {
        result += bytes[index].toString(16).padStart(2, "0");
    }
    return result;
}

function installHooks() {
    if (hooksInstalled) {
        return true;
    }
    const module = Process.findModuleByName(MODULE_NAME);
    if (module === null) {
        return false;
    }

    for (const [operation, exportName] of EXPORTS) {
        const address = module.findExportByName(exportName);
        if (address === null) {
            send({kind: "error", message: `missing export ${exportName}`});
            continue;
        }
        Interceptor.attach(address, {
            onEnter(args) {
                this.vendorId = args[0].toUInt32() & 0xffff;
                this.productId = args[1].toUInt32() & 0xffff;
                this.device = args[2].toUInt32() & 0xff;
                this.data = args[3];
                this.size = args[4].toUInt32() & 0xff;
                this.operation = operation;
                if (operation === "write") {
                    this.dataHex = bufferToHex(this.data, this.size);
                }
            },
            onLeave(retval) {
                if (this.operation === "read") {
                    this.dataHex = bufferToHex(this.data, this.size);
                }
                send({
                    kind: "trace",
                    operation: this.operation,
                    vendor_id: this.vendorId,
                    product_id: this.productId,
                    device: this.device,
                    size: this.size,
                    data_hex: this.dataHex,
                    result: retval.toInt32(),
                });
            },
        });
    }
    hooksInstalled = true;
    send({kind: "status", message: "GHidApi hooks installed"});
    return true;
}

if (!installHooks()) {
    const timer = setInterval(() => {
        if (installHooks()) {
            clearInterval(timer);
        }
    }, 250);
}
"""


def normalize_trace_event(
    payload: Mapping[str, object],
    *,
    process_id: int,
    process_name: str,
    timestamp: str,
) -> dict[str, object]:
    operation = payload.get("operation")
    if operation not in TRACE_OPERATIONS:
        raise ValueError(f"unsupported trace operation: {operation!r}")

    data_hex = payload.get("data_hex")
    if not isinstance(data_hex, str):
        raise ValueError("trace data_hex must be a string")

    return {
        "timestamp": timestamp,
        "process": {"pid": process_id, "name": process_name},
        "operation": operation,
        "vendor_id": int(payload["vendor_id"]),
        "product_id": int(payload["product_id"]),
        "device": int(payload["device"]),
        "size": int(payload["size"]),
        "data_hex": data_hex.upper(),
        "result": int(payload["result"]),
    }


def select_process[ProcessInfoT: ProcessInfo](
    processes: list[ProcessInfoT],
    *,
    process_name: str,
    process_id: int | None = None,
) -> ProcessInfoT:
    if process_id is not None:
        for process in processes:
            if process.pid == process_id:
                return process
        raise LookupError(f"process id {process_id} was not found")

    expected_name = process_name.casefold()
    for process in processes:
        if process.name.casefold() == expected_name:
            return process
    raise LookupError(f"process {process_name!r} was not found")


def write_jsonl(path: Path, record: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
        output.write("\n")


def _non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return parsed


def _default_output_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path("build") / "traces" / f"gcc-hid-{stamp}.jsonl"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Observe GCC calls to GHidApi.dll without modifying them.",
    )
    parser.add_argument("--process", default="GCC.exe", help="process name to attach")
    parser.add_argument("--pid", type=int, help="exact process id to attach")
    parser.add_argument(
        "--wait-seconds",
        type=_non_negative_float,
        default=120.0,
        help="maximum time to wait for the process",
    )
    parser.add_argument(
        "--duration-seconds",
        type=_non_negative_float,
        default=0.0,
        help="capture duration; zero runs until Ctrl+C",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_default_output_path(),
        help="JSONL output path",
    )
    return parser


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _wait_for_process(
    device: Any,
    *,
    process_name: str,
    process_id: int | None,
    wait_seconds: float,
) -> ProcessInfo:
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            return select_process(
                device.enumerate_processes(),
                process_name=process_name,
                process_id=process_id,
            )
        except LookupError:
            if time.monotonic() >= deadline:
                target = f"pid {process_id}" if process_id is not None else process_name
                raise RuntimeError(f"timed out waiting for {target}") from None
            time.sleep(0.25)


def run_capture(args: argparse.Namespace) -> int:
    import frida

    device = frida.get_local_device()
    process = _wait_for_process(
        device,
        process_name=args.process,
        process_id=args.pid,
        wait_seconds=args.wait_seconds,
    )
    output_path = args.output.resolve()
    session = device.attach(process.pid)
    script = session.create_script(FRIDA_AGENT)
    trace_count = 0

    def on_message(message: Mapping[str, object], _data: object) -> None:
        nonlocal trace_count
        if message.get("type") != "send":
            print(f"Frida agent error: {message}", file=sys.stderr, flush=True)
            return
        payload = message.get("payload")
        if not isinstance(payload, Mapping):
            print(f"Invalid Frida payload: {payload!r}", file=sys.stderr, flush=True)
            return
        kind = payload.get("kind")
        if kind == "status":
            print(str(payload.get("message", "agent ready")), flush=True)
            return
        if kind == "error":
            print(f"Frida agent error: {payload.get('message')}", file=sys.stderr, flush=True)
            return
        if kind != "trace":
            return
        try:
            event = normalize_trace_event(
                payload,
                process_id=process.pid,
                process_name=process.name,
                timestamp=_utc_timestamp(),
            )
        except (KeyError, TypeError, ValueError) as error:
            print(f"Invalid trace event: {error}", file=sys.stderr, flush=True)
            return
        write_jsonl(output_path, event)
        trace_count += 1
        data_hex = str(event["data_hex"])
        command = data_hex[2:4] if len(data_hex) >= 4 else "--"
        print(
            f"{trace_count:05d} {event['operation']} size={event['size']} "
            f"command=0x{command} result={event['result']}",
            flush=True,
        )

    script.on("message", on_message)
    print(f"Attaching to {process.name} (pid {process.pid})", flush=True)
    print(f"Writing trace events to {output_path}", flush=True)
    try:
        script.load()
        deadline = (
            time.monotonic() + args.duration_seconds
            if args.duration_seconds > 0
            else None
        )
        while deadline is None or time.monotonic() < deadline:
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("Capture interrupted.", flush=True)
    finally:
        try:
            script.unload()
        finally:
            session.detach()
    print(f"Captured {trace_count} HID calls.", flush=True)
    return 0


def main() -> int:
    args = build_parser().parse_args()
    try:
        return run_capture(args)
    except Exception as error:
        print(f"Capture failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
