# Nollie HID Protocol Notes

Static source: `NollieRGB.exe`, build timestamp 2026-05-07, PyInstaller Python 3.11.

The archive contains `app.core_driver.n_dev_config` and
`app.core_driver.n_usb_driver`. The following behavior was recovered with
`pyi-archive_viewer`, `pyinstxtractor-ng`, and `pydisasm`.

- HID reports are `[0x00 report-id] + payload + zero padding` to `tx_len + 1`.
- `HID_SET_EFFECT = 250`; `HID_GET_EFFECT = 249`.
- `HID_EFFECT_CH_PARAM = 2`; `HID_EFFECT_CANVAS_LEN = 4`.
- Canvas count read payload: `[249, 4]`; count is response byte 0.
- Canvas config read payload: `[249, 2, canvas]`.
- Config response fields are bytes 3 through 18. Brightness is byte 4.
- Config write payload is `[250, 2, canvas]` followed by all 16 config bytes.
- Default read timeout is 20 ms with two retries and 5 ms retry delay.
- Unknown VID/PID/interface triplets are not opened.

The device table in `src/nollie_rgb_idle/discovery.py` includes only current
application-mode devices from the recovered catalog. Bootloaders and legacy
devices are intentionally excluded from writes.
