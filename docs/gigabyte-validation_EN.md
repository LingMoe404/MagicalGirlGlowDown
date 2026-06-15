# Gigabyte RGB Hardware Validation

[简体中文](gigabyte-validation.md)

## Read-Only Probe

Close GCC, then run:

```powershell
uv run magical-girl-glow-down --gigabyte-probe --debug
```

This command reads:

- Windows motherboard identity from the BIOS registry key;
- GCC assembly file versions;
- saved zone count from `RGBMotherboard/Profile-0.xml`.

It does not initialize the RGB controller and does not call any vendor lighting
method. Unmapped profile positions are reported as `unsupported`; they remain
write-disabled until their vendor identities are confirmed.

## Validated Board Layout

For `X870E AORUS MASTER X3D ICE`, the installed GCC 26.03.25.01 UI geometry
matches `rgbcfg.xml` layout `98`. The seven saved profile positions are:

| Profile index | GCC zone | Category |
| --- | --- | --- |
| 0 | LED_C | 12V RGB |
| 1 | ARGB_V2_1 | 5V ARGB |
| 2 | ARGB_V2_2 | 5V ARGB |
| 3 | ARGB_V2_3 | 5V ARGB |
| 4 | ARGB_V2_4 | 5V ARGB |
| 5 | IO Shield LED | Onboard |
| 6 | PCH LED | Onboard |

The mapping was checked against the board layout in Gigabyte's official manual
and the coordinates rendered by the locally installed GCC. It is selected only
for this exact product name; other boards remain unsupported.

## Write Safety

Hardware writes must not be enabled until:

1. the board fingerprint matches the current machine;
2. each writable zone has an explicit `onboard`, `argb5v`, or `rgb12v`
   classification;
3. snapshot readback has been validated;
4. GCC is closed;
5. automatic restoration is armed.

The integration never calls BIOS-save, calibration-write, or firmware-update
methods.

The temporary blackout path is intentionally limited to three vendor runtime
operations:

- `GetLedSetting()` captures the complete vendor JSON state;
- `SetAllLedColor(0)` turns every validated motherboard/header zone black;
- `sInfo = <captured JSON>` followed by `Apply(3)` restores that exact state.

`SaveSetting`, BIOS power-state operations, calibration methods, and profile
writes are not on the helper whitelist.

## Staged Runtime Test

Close GCC before either command. A snapshot does not change the lights:

```powershell
uv run magical-girl-glow-down --gigabyte-snapshot --debug
```

The snapshot and write commands request administrator permission because GCC's
native motherboard controller reports no MB/LED identity to a standard user
process. The read-only `--gigabyte-probe` command remains non-elevated.

The following command turns off all seven validated zones and restores them
after five seconds, including effect, colors, speed, brightness, and vendor
extension fields:

```powershell
uv run magical-girl-glow-down --gigabyte-test-all --restore-after 5 --debug
```

The restore delay must be from 1 through 30 seconds. Restoration runs from a
`finally` block, including cancellation paths. The helper refuses snapshot,
blackout, and restore operations while `GCC.exe` is running.

## Hardened Security Boundaries and Recovery Policies

To ensure the security and recovery reliability of motherboard lighting control under administrative privileges, the following mechanisms are implemented:

1. **Packaged Run Isolation**: In packaged releases, any environment path overrides (`MAGICALGIRLGLOWDOWN_GIGABYTE_HELPER` and `MAGICALGIRLGLOWDOWN_GCC_ROOT`) are strictly ignored. The program searches for GCC components exclusively under the fixed path `%ProgramFiles%\GIGABYTE\Control Center`, preventing path injection and hijacking.
2. **Protected Staging and Storage Directories**: The C# helper DLL staging area and the Python recovery state are located under `%ProgramData%\MagicalGirlGlowDown`. This directory enforces an ACL limiting write access exclusively to the built-in Administrators group and SYSTEM. On startup, the program verifies that neither this directory nor its parents are reparse points (symbolic links/junctions). Any detected reparse point leads to an immediate termination to prevent privilege escalation.
3. **GCC Conflict and Snapshot Preservation**: If GCC starts during blackout, the tool yields motherboard control. If the handoff causes a restore failure, the snapshot is marked `pending_restore` and safely preserved in `%ProgramData%\MagicalGirlGlowDown\state.json`. Once GCC is closed, the tool priority-restores this pending state before resuming normal idle loops, ensuring hardware configurations are never lost.
