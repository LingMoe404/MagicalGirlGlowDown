from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from .simulator import run_simulation


def _restore_delay(value: str) -> float:
    delay = float(value)
    if not 1 <= delay <= 30:
        raise argparse.ArgumentTypeError("restore delay must be between 1 and 30 seconds")
    return delay


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nollie-rgb-idle")
    parser.add_argument("--simulate", action="store_true", help="run without HID hardware")
    parser.add_argument("--cycles", type=int, default=1)
    parser.add_argument("--idle-seconds", type=float)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--install-autostart", action="store_true")
    parser.add_argument("--remove-autostart", action="store_true")
    parser.add_argument(
        "--gigabyte-probe",
        action="store_true",
        help="read GCC motherboard and zone metadata without changing lighting",
    )
    parser.add_argument(
        "--gigabyte-snapshot",
        action="store_true",
        help="capture current Gigabyte lighting state without changing it",
    )
    parser.add_argument(
        "--gigabyte-test-all",
        action="store_true",
        help="temporarily turn off every validated Gigabyte zone",
    )
    parser.add_argument(
        "--restore-after",
        type=_restore_delay,
        default=5.0,
        help="seconds before automatic restore during --gigabyte-test-all",
    )
    return parser


def app_data_dir() -> Path:
    root = os.getenv("LOCALAPPDATA")
    if root:
        return Path(root) / "NollieRGBIdle"
    return Path.home() / ".nollie-rgb-idle"


async def _simulate(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory(prefix="NollieRGBIdle-") as directory:
        result = await run_simulation(
            Path(directory),
            idle_seconds=args.idle_seconds or 30.0,
            cycles=args.cycles,
        )
    print(f"dimmed={result.dimmed}")
    print(f"restored={result.restored}")
    return 0


async def _gigabyte_snapshot() -> dict[str, object]:
    from .gigabyte import GigabyteHelperClient

    client = GigabyteHelperClient()
    probe = await client.probe()
    return await client.snapshot(
        probe.board_fingerprint,
        tuple(zone.id for zone in probe.zones),
    )


async def _gigabyte_test_all(restore_after: float) -> int:
    from .gigabyte import GigabyteHelperClient

    client = GigabyteHelperClient()
    probe = await client.probe()
    zones = tuple(zone.id for zone in probe.zones)
    snapshot = await client.snapshot(probe.board_fingerprint, zones)
    try:
        await client.blackout(probe.board_fingerprint, snapshot)
        print(f"Gigabyte lighting is off; restoring in {restore_after:g} seconds")
        await asyncio.sleep(restore_after)
    finally:
        await client.restore(probe.board_fingerprint, snapshot)
    print("Gigabyte lighting restored")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    if args.simulate:
        return asyncio.run(_simulate(args))
    if args.gigabyte_probe:
        from .gigabyte import GigabyteHelperClient

        probe = asyncio.run(GigabyteHelperClient().probe())
        print(
            json.dumps(
                {
                    "board_fingerprint": probe.board_fingerprint,
                    "board": probe.board,
                    "assembly_versions": probe.assembly_versions,
                    "zones": [
                        {
                            "id": zone.id,
                            "category": zone.category,
                            "name": zone.name,
                        }
                        for zone in probe.zones
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.gigabyte_snapshot:
        print(
            json.dumps(
                asyncio.run(_gigabyte_snapshot()),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.gigabyte_test_all:
        return asyncio.run(_gigabyte_test_all(args.restore_after))
    if args.install_autostart or args.remove_autostart:
        from .autostart import AutostartManager, WindowsRunRegistry

        command = subprocess.list2cmdline(
            [sys.executable, "-m", "nollie_rgb_idle.main"]
        )
        manager = AutostartManager(WindowsRunRegistry(), command)
        if args.install_autostart:
            manager.enable()
            print("NollieRGBIdle autostart enabled")
        else:
            manager.disable()
            print("NollieRGBIdle autostart disabled")
        return 0
    from .tray import run_tray

    return run_tray(args.idle_seconds, app_data_dir())


if __name__ == "__main__":
    raise SystemExit(main())
