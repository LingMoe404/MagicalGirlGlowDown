from __future__ import annotations

from nollie_rgb_idle.discovery import normalize_hid_device
from nollie_rgb_idle.protocol import (
    HID_EFFECT_CH_PARAM,
    HID_GET_EFFECT,
    HID_SET_EFFECT,
    GeneralConfig,
    encode_report,
    parse_general_config,
)


def test_encode_report_matches_original_driver_framing() -> None:
    report = encode_report([HID_GET_EFFECT, HID_EFFECT_CH_PARAM, 1], tx_len=64)
    assert len(report) == 65
    assert report[:4] == bytes([0, 249, 2, 1])
    assert set(report[4:]) == {0}


def test_parse_and_rewrite_general_config_brightness() -> None:
    response = bytes([0, 0, 0, 9, 30, 2, 4, 1, 0, 7, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    config = parse_general_config(response)
    assert config.brightness == 30
    assert config.with_brightness(0).to_payload(1) == bytes(
        [HID_SET_EFFECT, HID_EFFECT_CH_PARAM, 1, 9, 0, 2, 4, 1, 0, 7, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    )


def test_hid_normalization_rejects_unknown_devices() -> None:
    assert normalize_hid_device({"vendor_id": 1, "product_id": 2, "interface_number": 0}) is None
    device = normalize_hid_device(
        {
            "vendor_id": 5845,
            "product_id": 10774,
            "interface_number": 0,
            "path": b"hid-path",
            "serial_number": "ABC",
        }
    )
    assert device is not None
    assert device.model == "Nollie16"
    assert device.tx_len == 1024


def test_general_config_rejects_invalid_brightness() -> None:
    config = GeneralConfig(1, 30, 1, 1, 1, 0, 0, (1, 2, 3), (4, 5, 6), (7, 8, 9))
    assert config.with_brightness(100).brightness == 100
