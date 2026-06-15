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

from .branding import (
    APP_NAME,
    CLI_NAME,
    DATA_DIR_NAME,
    set_windows_app_id,
)
from .runtime import runtime_command
from .simulator import run_simulation


def _restore_delay(value: str) -> float:
    delay = float(value)
    if not 1 <= delay <= 30:
        raise argparse.ArgumentTypeError("restore delay must be between 1 and 30 seconds")
    return delay


def _positive_finite_float(value: str) -> float:
    import math

    parsed = float(value)
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a finite number greater than zero")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=CLI_NAME)
    parser.add_argument("--simulate", action="store_true", help="run without HID hardware")
    parser.add_argument("--cycles", type=int, default=1)
    parser.add_argument("--idle-seconds", type=_positive_finite_float)

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
        return Path(root) / DATA_DIR_NAME
    return Path.home() / f".{CLI_NAME}"


async def _simulate(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory(prefix=f"{APP_NAME}-") as directory:
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
    from .privilege import is_elevated, relaunch_elevated, requires_elevation

    if (
        requires_elevation(
            simulate=args.simulate,
            gigabyte_probe=args.gigabyte_probe,
            gigabyte_snapshot=args.gigabyte_snapshot,
            gigabyte_test_all=args.gigabyte_test_all,
            install_autostart=args.install_autostart,
            remove_autostart=args.remove_autostart,
        )
        and not is_elevated()
    ):
        from .i18n import t
        if relaunch_elevated(sys.argv[1:]):
            return 0
        print(t("admin_needed"), file=sys.stderr)
        return 1
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
        from .autostart import AutostartManager, WindowsTaskScheduler

        command = subprocess.list2cmdline(runtime_command())
        manager = AutostartManager(WindowsTaskScheduler(), command)
        if args.install_autostart:
            manager.enable()
            print(f"{APP_NAME} autostart enabled")
        else:
            manager.disable()
            print(f"{APP_NAME} autostart disabled")
        return 0
    from .tray import run_tray

    set_windows_app_id()
    return run_tray(args.idle_seconds, app_data_dir())


if __name__ == "__main__":
    raise SystemExit(main())
