# NollieRGBIdle

Windows tray companion for Nollie RGB controllers and validated Gigabyte
motherboard lighting.

NollieRGBIdle watches global keyboard, mouse, XInput, WinMM, and Raw Input game
controller activity. After 30 seconds without input it saves every standby
canvas brightness and sets those brightness values to zero. Input restores the
saved values.

On the validated `X870E AORUS MASTER X3D ICE`, it also controls the motherboard
IO shield/PCH LEDs, four 5V ARGB headers, and one 12V RGB header through the
locally installed Gigabyte Control Center libraries. GCC must remain installed.
No Gigabyte DLL is bundled.

The original `NollieRGB.exe` does not need to remain open. If it is opened,
NollieRGBIdle restores lighting, releases its HID handles, and pauses writes.
If `GCC.exe` opens, only the Gigabyte backend yields ownership; Nollie
controllers continue operating. Two seconds after GCC closes, the motherboard
is probed again and GCC's latest effect becomes the next restorable state.

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
dotnet test helper/NollieRGBIdle.GigabyteHelper.Tests -c Release -v minimal
```

Build the isolated Gigabyte helper:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-helper.ps1
```

Run the deterministic two-controller simulator:

```powershell
uv run nollie-rgb-idle --simulate --cycles 1 --idle-seconds 0.1
```

Start the tray application:

```powershell
uv run nollie-rgb-idle
```

Read-only Gigabyte discovery:

```powershell
uv run nollie-rgb-idle --gigabyte-probe --debug
```

With GCC closed, capture the full vendor state or run a five-second automatic
blackout/restore test:

```powershell
uv run nollie-rgb-idle --gigabyte-snapshot --debug
uv run nollie-rgb-idle --gigabyte-test-all --restore-after 5 --debug
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

For Gigabyte validation, close GCC before starting. Confirm the two onboard
zones and any attached 5V/12V strips turn off after the timeout and return to
their exact effect after keyboard, mouse, or game-controller input. Open GCC
while idle and verify it takes ownership without stopping Nollie control.

The Gigabyte helper only whitelists temporary runtime state calls. It never
calls GCC profile saves, calibration writes, BIOS persistence, firmware update,
or a low-level SMBus fallback.

Protocol evidence is documented in [docs/protocol-notes.md](docs/protocol-notes.md).
Gigabyte validation details are in
[docs/gigabyte-validation.md](docs/gigabyte-validation.md).
