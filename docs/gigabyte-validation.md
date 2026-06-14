# Gigabyte RGB Hardware Validation

## Read-Only Probe

Close GCC, then run:

```powershell
uv run nollie-rgb-idle --gigabyte-probe --debug
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
