from __future__ import annotations

import argparse
import asyncio
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from .simulator import run_simulation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nollie-rgb-idle")
    parser.add_argument("--simulate", action="store_true", help="run without HID hardware")
    parser.add_argument("--cycles", type=int, default=1)
    parser.add_argument("--idle-seconds", type=float)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--install-autostart", action="store_true")
    parser.add_argument("--remove-autostart", action="store_true")
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


def main() -> int:
    args = build_parser().parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    if args.simulate:
        return asyncio.run(_simulate(args))
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
