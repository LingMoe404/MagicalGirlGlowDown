# Gigabyte RGB Support Design

## Objective

Extend NollieRGBIdle so the existing 30-second idle policy also controls the
lighting exposed by Gigabyte Control Center (GCC) on the current Gigabyte
motherboard.

The integration covers:

- motherboard-integrated lighting such as logos and armor;
- 5V addressable RGB headers when GCC exposes them as distinct controllable
  zones;
- 12V analog RGB headers when GCC exposes them as distinct controllable zones.

Before blackout, NollieRGBIdle captures each supported zone's complete current
state. Keyboard, mouse, or game-controller input restores that state. Unknown
zones and hardware that cannot be identified safely are left untouched.

## Safety Constraints

The Gigabyte integration must:

- use the vendor components already installed with GCC;
- never distribute Gigabyte DLLs in this repository or release artifacts;
- never use guessed direct SMBus, ACPI, I/O-port, or embedded-controller writes;
- never call BIOS-save, firmware-update, calibration-write, or other persistent
  configuration operations;
- never treat a partial or unvalidated snapshot as safe to black out;
- fail independently so existing Nollie controller support remains operational;
- perform no Gigabyte writes while GCC is running.

The first hardware validation is staged: read-only discovery first, followed by
one temporary blackout and immediate restore only after the detected board and
zones have been reviewed.

## Architecture

The Python application retains ownership of idle detection, policy, persistence,
tray status, and orchestration. Gigabyte hardware access lives in a small
out-of-process .NET helper.

The helper:

1. Locates the installed GCC directory at runtime.
2. Loads the compatible motherboard RGB assemblies from GCC, preferring the
   public managed interfaces in `RgbMotherboard.dll` and `LedIoControl.dll`.
3. Initializes the motherboard through the vendor API.
4. Reports the motherboard identity, available zones, capabilities, and current
   state as JSON.
5. Applies temporary blackout or restore requests only to validated zones.
6. Exits after each bounded request or when the Python parent closes the session.

Python communicates with the helper through versioned JSON messages over
standard input and output. Keeping the vendor assemblies outside the Python
process prevents a native or managed vendor failure from taking down the tray
application and avoids adding `pythonnet` to the main runtime.

The repository contains the helper source and build instructions, but not GCC
assemblies. At runtime, a missing or incompatible GCC installation marks the
Gigabyte backend unavailable without affecting Nollie devices.

## Components

### Gigabyte Helper

The helper exposes four operations:

- `probe`: identify the board, GCC assembly versions, zones, and capabilities
  without changing lighting;
- `snapshot`: return complete restorable state for every selected zone;
- `blackout`: temporarily turn selected zones off without persistent saving;
- `restore`: restore an earlier validated snapshot and verify the result where
  readback is available.

The protocol includes a schema version, request ID, board fingerprint, and
structured errors. Diagnostic output goes to standard error so it cannot corrupt
JSON responses.

### Gigabyte Backend

The Python backend starts the helper with a timeout, validates its response, and
adapts it to a generic lighting-target interface. A target snapshot is opaque to
the common idle service except for identity, version, and pending-restore state.

This generalizes the current brightness-only service without changing the
Nollie HID protocol:

- Nollie targets continue to store standby-canvas brightness tuples.
- Gigabyte targets store per-zone effect, color, brightness, speed, power, and
  any vendor fields required for exact restoration.

### GCC Guard

Process monitoring treats `GCC.exe` and its relevant RGB configuration process
as exclusive owners of Gigabyte lighting.

When GCC starts:

1. Restore any Gigabyte snapshot that NollieRGBIdle currently has applied.
2. Stop the Gigabyte helper and release vendor resources.
3. Pause only the Gigabyte backend.
4. Continue normal Nollie controller handling unless `NollieRGB.exe` is also
   running.

When GCC exits, the backend waits for a short settling interval, performs a new
read-only probe, and resumes from the lighting state GCC left active. It never
restores stale pre-GCC values over changes made by the user in GCC.

## Zone Selection

The helper includes a zone only when the GCC API provides a stable identity and
enough information to snapshot and restore it.

Supported categories are:

- onboard motherboard illumination;
- 5V ARGB headers;
- 12V RGB headers.

Each detected zone records its vendor identifier, category, display name, and
capabilities. Category selection is explicit; no positional assumptions from a
different motherboard model are allowed.

If a header is present but GCC does not distinguish it safely, the helper reports
it as unsupported and performs no write. Headers do not need attached LEDs to be
enumerated, but absent or unreadable zones are skipped.

## State Flow

On transition to idle:

1. Confirm GCC is not running.
2. Probe the helper and validate that the motherboard fingerprint still matches.
3. Read a complete snapshot from each supported Gigabyte zone.
4. Atomically persist the snapshot with `pending_restore` set.
5. Request a temporary blackout for exactly those zones.
6. Verify the result where the GCC API supports readback.

On user input:

1. Cancel any pending blackout request.
2. Confirm GCC is not running and the board fingerprint matches.
3. Restore all pending Gigabyte zone snapshots.
4. Clear `pending_restore` only after successful application.
5. Retain failed snapshots for a later retry.

Startup recovery follows the same restore path before normal idle monitoring.
Exit, pause, logoff, and shutdown request restoration.

## Persistence

Gigabyte snapshots are stored separately from Nollie brightness snapshots under
`%LOCALAPPDATA%\NollieRGBIdle`.

A snapshot contains:

- motherboard manufacturer, product name, and vendor-derived board identity;
- GCC and helper protocol versions;
- zone identities and categories;
- complete opaque restorable state per zone;
- capture time and pending-restore marker.

Atomic replacement is used for writes. A snapshot captured from a different
board identity or incompatible helper schema is never applied automatically.

## Error Handling

- GCC missing: report the backend as unavailable and continue controlling Nollie
  devices.
- Vendor DLL mismatch: stop before hardware writes and include assembly versions
  in diagnostics.
- GCC starts during an operation: abort the operation, restore if safe, release
  the helper, and enter the Gigabyte-paused state.
- Helper crash or timeout: terminate it, retain pending recovery data, and retry
  later with bounded backoff.
- Partial snapshot: do not black out any Gigabyte zone in that transaction.
- Unsupported zone: report and skip it.
- Board fingerprint mismatch: refuse restoration and require a fresh snapshot.
- Restore failure: keep the recovery marker and expose the error through the tray
  and logs.

No automatic fallback performs low-level motherboard writes.

## User Experience

Gigabyte support is enabled automatically when a compatible GCC installation and
motherboard are detected. The tray status distinguishes:

- Gigabyte active;
- Gigabyte dimmed;
- Gigabyte paused because GCC is open;
- Gigabyte unavailable or unsupported;
- Gigabyte restore pending or failed.

The existing enable, idle-timeout, restore-now, and input behavior applies to
both Nollie and Gigabyte targets. Diagnostics list discovered zone names and
categories but do not expose raw memory or bus data.

## Testing

Automated Python tests cover:

- helper protocol parsing and timeouts;
- fan-out across Nollie and Gigabyte targets;
- persistence of opaque per-zone snapshots;
- GCC start, restore, pause, and fresh-state resume behavior;
- board fingerprint mismatch;
- partial snapshot and partial restore failures;
- helper crashes without interruption to Nollie controllers.

Automated .NET tests use fake vendor adapters to cover:

- zone classification;
- full-state serialization;
- exclusion of unknown zones;
- prohibition of persistent-save methods;
- blackout and exact restore;
- readback verification and structured errors.

Hardware acceptance on the current `X870E AORUS MASTER X3D ICE` proceeds in this
order:

1. Close GCC and run `probe` only.
2. Review the detected board identity, onboard zones, 5V headers, and 12V
   headers.
3. Capture and print a snapshot without writing.
4. Black out one confirmed onboard zone and immediately restore it.
5. Repeat for one confirmed 5V and one confirmed 12V header when attached
   lighting is available.
6. Black out all supported zones and restore them on keyboard, mouse, and
   game-controller input.
7. Open GCC while NollieRGBIdle is active and confirm restoration and pause.
8. Change an effect in GCC, close GCC, and confirm NollieRGBIdle adopts the new
   state rather than restoring stale values.
9. Test restart recovery and helper-failure isolation.

No hardware write test proceeds when the read-only probe cannot establish a
supported board and unambiguous zone identities.

## Delivery Scope

The feature delivers:

- a source-built .NET helper and versioned JSON protocol;
- a Python Gigabyte lighting backend;
- generalized snapshot orchestration for multiple lighting target types;
- GCC coexistence handling;
- recovery persistence, diagnostics, and automated tests;
- staged hardware-validation commands.

Direct motherboard bus control, GCC installation, firmware changes, BIOS
persistence, and support for unidentified third-party RGB controllers are out of
scope.
