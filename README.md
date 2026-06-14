# NollieRGBIdle

Windows tray companion for Nollie RGB controllers.

NollieRGBIdle watches global keyboard, mouse, XInput, WinMM, and Raw Input game
controller activity. After 30 seconds without input it saves every standby
canvas brightness and sets those brightness values to zero. Input restores the
saved values.

The original `NollieRGB.exe` does not need to remain open. If it is opened,
NollieRGBIdle restores lighting, releases its HID handles, and pauses writes.

## Current Status

The application, simulator, protocol codec, supported-device discovery, recovery
storage, Windows input monitors, tray UI, and autostart commands are implemented.

Offline tests cannot prove physical-device behavior. HID commands were recovered
from the Python 3.11 bytecode in the 2026-05-07 NollieRGB build and fail closed
for unknown VID/PID/interface combinations. A real controller is still required
for final hardware acceptance.

## Development

Install Python 3.11 and [uv](https://docs.astral.sh/uv/), then run:

```powershell
uv sync --all-groups
uv run pytest
uv run ruff check .
uv run mypy src
```

Run the deterministic two-controller simulator:

```powershell
uv run nollie-rgb-idle --simulate --cycles 1 --idle-seconds 0.1
```

Start the tray application:

```powershell
uv run nollie-rgb-idle
```

## Autostart

Enable per-user startup:

```powershell
uv run nollie-rgb-idle --install-autostart
```

Remove it:

```powershell
uv run nollie-rgb-idle --remove-autostart
```

The startup entry is stored under
`HKCU\Software\Microsoft\Windows\CurrentVersion\Run` and needs no administrator
privileges.

## Supported Controllers

The recovered current-device catalog includes Nollie1, Nollie8, Prism8,
Nollie16, Nollie32, and G857D application-mode HID interfaces. Bootloaders,
legacy firmware interfaces, and unknown hardware revisions are deliberately not
written.

## Hardware Validation

When a controller is available:

1. Export a NollieRGB configuration backup.
2. Close `NollieRGB.exe`.
3. Start NollieRGBIdle with `--debug`.
4. Confirm controller discovery without changing lighting.
5. Wait 30 seconds and confirm all standby canvases turn off.
6. Press a key, move the mouse, and use each connected game controller.
7. Confirm the exact prior brightness values return.
8. Repeat with multiple controllers and hot-plugging.
9. Open `NollieRGB.exe` and confirm NollieRGBIdle restores, releases, and pauses.
10. Force-close NollieRGBIdle while dimmed, restart it, and confirm recovery.

Protocol evidence is documented in [docs/protocol-notes.md](docs/protocol-notes.md).
