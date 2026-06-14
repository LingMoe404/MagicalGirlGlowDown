from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .protocol import NollieController


@dataclass(frozen=True, slots=True)
class DeviceSpec:
    model: str
    vendor_id: int
    product_id: int
    interface_number: int
    tx_len: int
    rx_len: int
    channel_count: int


# Recovered from app.core_driver.n_dev_config in NollieRGB.exe (2026-05-07 build).
DEVICE_SPECS = (
    DeviceSpec("Nollie1", 5845, 10753, 2, 64, 64, 1),
    DeviceSpec("Nollie8", 5845, 10760, 2, 64, 64, 8),
    DeviceSpec("Prism8", 5845, 11272, 2, 64, 64, 8),
    DeviceSpec("Nollie16", 5845, 10774, 0, 1024, 1024, 16),
    DeviceSpec("Nollie32", 5845, 10802, 0, 1024, 1024, 32),
    DeviceSpec("G857D", 6790, 58136, 2, 64, 64, 8),
)


@dataclass(frozen=True, slots=True)
class HidDevice:
    model: str
    path: bytes | str
    serial: str | None
    tx_len: int
    rx_len: int
    channel_count: int

    @property
    def path_text(self) -> str:
        if isinstance(self.path, bytes):
            return self.path.decode(errors="replace")
        return str(self.path)


def normalize_hid_device(value: Mapping[str, Any]) -> HidDevice | None:
    try:
        triplet = (
            int(value["vendor_id"]),
            int(value["product_id"]),
            int(value["interface_number"]),
        )
    except (KeyError, TypeError, ValueError):
        return None
    for spec in DEVICE_SPECS:
        if triplet == (spec.vendor_id, spec.product_id, spec.interface_number):
            path = value.get("path")
            if not isinstance(path, (bytes, str)):
                return None
            serial = value.get("serial_number")
            return HidDevice(
                model=spec.model,
                path=path,
                serial=None if serial is None else str(serial),
                tx_len=spec.tx_len,
                rx_len=spec.rx_len,
                channel_count=spec.channel_count,
            )
    return None


def discover_controllers() -> list[NollieController]:
    import hid

    controllers: list[NollieController] = []
    for record in hid.enumerate():
        device = normalize_hid_device(record)
        if device is None:
            continue
        try:
            controllers.append(NollieController(device))
        except OSError:
            continue
    return controllers
