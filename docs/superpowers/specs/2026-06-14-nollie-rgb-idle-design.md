# NollieRGBIdle Design

## Objective

Build an independent Windows background application that controls every connected
Nollie RGB controller without requiring `NollieRGB.exe` to run.

After 30 seconds without keyboard, mouse, or game-controller input, the
application sets the brightness of every standby canvas on every controller to
zero. Any supported input immediately restores the exact brightness values that
were active before dimming.

The original installation at `D:\Program Files Portable\NollieRGB` remains
unmodified and is used only as a read-only protocol-analysis reference.

## User Experience

- The application starts automatically after Windows sign-in.
- It normally runs in the notification area without opening a window.
- The tray icon exposes the current state: active, idle/dimmed, paused, no
  controller, or communication error.
- The tray menu supports pause/resume, restore lighting now, open settings, and
  exit.
- The default idle timeout is 30 seconds.
- User input restores lighting immediately.
- All connected Nollie controllers are handled together.
- Connecting or disconnecting controllers does not require restarting the
  application.

## Architecture

The application is a Python 3.11 project managed by `uv`. Development startup is:

```powershell
uv run nollie-idle
```

The code is divided into independent components:

1. `idle_monitor`: combines Windows keyboard/mouse idle time with game-controller
   activity and emits active/idle transitions.
2. `controller_discovery`: detects supported Nollie HID devices and reports
   hot-plug events.
3. `nollie_protocol`: owns packet formats and read/write operations derived from
   the packaged NollieRGB application.
4. `brightness_service`: snapshots standby-canvas brightness, dims controllers,
   restores snapshots, and coordinates retries.
5. `state_store`: persists only recovery-critical state and application settings.
6. `app_guard`: detects `NollieRGB.exe` and prevents simultaneous writes.
7. `tray_app`: displays status and exposes user actions.

Hardware access is behind a narrow protocol interface so the rest of the
application can run against a deterministic simulated controller.

## Input Detection

Keyboard and mouse activity uses Windows `GetLastInputInfo`, which works globally
without installing hooks or recording key contents.

Game-controller activity is detected through three complementary paths:

- XInput polling for Xbox-compatible controllers.
- WinMM joystick polling for older DirectInput-style devices.
- Raw Input HID registration with background input enabled for generic USB and
  Bluetooth controllers.

Only activity timestamps and coarse device identity are retained. Button names,
key values, text, and movement history are not logged.

Raw analog noise must not continuously wake the lighting. Axis input counts as
activity only after crossing a configurable dead zone or changing beyond a
stable threshold. Buttons, hats, triggers, connect events, and disconnect events
are handled explicitly.

This covers controllers that expose input through standard Windows APIs. Devices
that expose no Windows input reports outside a proprietary vendor process cannot
be guaranteed.

## Device Protocol Strategy

The packaged application is inspected offline to recover:

- supported USB vendor/product identifiers;
- HID report framing and report IDs;
- commands for reading controller/canvas configuration;
- commands for writing standby-canvas brightness;
- acknowledgement, timeout, and retry behavior;
- controller model and channel-count differences.

Protocol discovery may extract and inspect PyInstaller bytecode, but the
resulting product does not depend on decompiled application code at runtime.
Only the minimal protocol required for discovery, brightness reads, and
brightness writes is implemented.

The implementation must prefer a controller-level temporary brightness or
blackout command if the protocol exposes one that preserves all canvas
configuration. If no such command exists, it falls back to setting each standby
canvas brightness to zero and later restoring the captured values.

## Brightness State Machine

The service has five states:

- `ACTIVE`: input occurred recently; controllers retain their configured values.
- `DIMMING`: current brightness values are being captured and zeroed.
- `DIMMED`: all reachable controllers have been dimmed.
- `RESTORING`: captured values are being written back.
- `PAUSED`: no automatic device writes are allowed.

On the transition from active to idle:

1. Read every reachable controller's current standby-canvas brightness.
2. Validate the complete snapshot.
3. Persist the snapshot atomically.
4. Dim that controller.
5. Never replace a valid nonzero recovery snapshot with values read while the
   controller is already dimmed.

On any input:

1. Cancel pending dim operations.
2. Restore every controller with a valid snapshot.
3. Keep retrying transient failures with bounded backoff.
4. Remove the persisted recovery marker only after the controller confirms the
   restored state.

If a global temporary brightness command is available, the snapshot still
records enough state to recover after a crash or restart.

## Coexistence With NollieRGB

`NollieRGBIdle` monitors for `NollieRGB.exe`.

When the original application starts:

1. Restore any dimmed controllers.
2. Stop all automatic device writes.
3. Release HID handles where the protocol requires exclusive access.
4. Enter `PAUSED` and explain the reason in the tray status.

When the original application exits, automatic operation resumes after a short
settling delay and a fresh controller scan.

No DLL injection, UI automation, executable patching, or process-memory editing
is used.

## Persistence And Recovery

Application data is stored under `%LOCALAPPDATA%\NollieRGBIdle`.

Persistent data includes:

- idle timeout and controller-input dead-zone settings;
- whether automatic control is enabled;
- per-controller serial/model identity;
- the last known valid pre-dim brightness snapshot;
- whether a restore was still pending when the process stopped.

Writes use a temporary file followed by atomic replacement. On startup, a
pending restore is attempted before normal idle monitoring begins.

Normal exit, pause, Windows shutdown, and user logoff request restoration.
Because abrupt power loss cannot run cleanup code, the persisted snapshot is the
authoritative recovery path on the next launch.

## Error Handling

- No controller: remain running and wait for hot-plug.
- One controller fails: continue processing other controllers and retain the
  failed controller's recovery state.
- Partial snapshot: do not dim that controller.
- Write timeout: retry with bounded exponential backoff and show an error state.
- Unsupported firmware/model: do not send guessed packets; report it as
  unsupported.
- Corrupt state file: quarantine it, do not write brightness, and present a
  recoverable warning.
- Original application detected: restore and pause rather than competing for
  the device.

Logs contain state transitions, device identities, command names, and errors,
but never keyboard text or raw controller input streams.

## Settings

The first release exposes:

- enable/disable automatic dimming;
- idle timeout, default 30 seconds;
- launch at Windows sign-in;
- controller axis dead-zone;
- restore now;
- diagnostic logging.

Autostart uses a per-user Windows startup registration and does not require
administrator privileges. Installation and removal must be reversible.

## Testing

Offline automated tests cover:

- active-to-idle and idle-to-active state transitions;
- keyboard/mouse timestamp integration;
- XInput, WinMM, and Raw Input event normalization;
- analog dead-zone and noise rejection;
- all-controller fan-out;
- hot-plug during active, dimmed, and restoring states;
- snapshot atomicity and crash recovery;
- prevention of zero-overwriting a valid recovery snapshot;
- original-application coexistence;
- retry and partial-failure behavior;
- protocol packet encode/decode fixtures recovered from static analysis.

A fake protocol transport simulates multiple controller models, disconnects,
timeouts, malformed responses, and acknowledgements.

Offline acceptance requires:

```powershell
uv sync
uv run pytest
uv run nollie-idle --simulate
```

The simulator must demonstrate multiple controllers dimming after 30 seconds and
restoring on synthetic keyboard, mouse, XInput, WinMM, and generic HID activity.

True hardware acceptance is deferred until a controller is available. It must
verify device discovery, readback, dimming, restoration, hot-plug, restart
recovery, and coexistence with the original NollieRGB application.

## Delivery Scope

The initial delivery includes:

- a complete `uv` Python project;
- tray background application;
- Windows autostart support;
- multi-controller input and brightness orchestration;
- simulated controller mode and automated tests;
- offline-derived Nollie protocol implementation where static evidence is
  sufficient;
- a clear hardware-validation checklist for any behavior that cannot be proven
  without a physical controller.

Recreating or modifying the full NollieRGB user interface is out of scope.
