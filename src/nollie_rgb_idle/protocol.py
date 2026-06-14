from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from typing import Any, Protocol

from .domain import ControllerId
from .lighting import LightingError, TargetIdentity

HID_SET_EFFECT = 250
HID_GET_EFFECT = 249
HID_EFFECT_CH_PARAM = 2
HID_EFFECT_CANVAS_LEN = 4
READ_TIMEOUT_MS = 20


def encode_report(payload: list[int] | bytes, tx_len: int) -> bytes:
    if len(payload) > tx_len:
        raise ValueError("payload exceeds HID report length")
    return b"\x00" + bytes(payload) + bytes(tx_len - len(payload))


@dataclass(frozen=True, slots=True)
class GeneralConfig:
    mode: int
    brightness: int
    step: int
    size: int
    canvas_channel_count: int
    vmap_process: int
    delay: int
    color_1: tuple[int, int, int]
    color_2: tuple[int, int, int]
    color_3: tuple[int, int, int]

    def with_brightness(self, value: int) -> GeneralConfig:
        if not 0 <= value <= 100:
            raise ValueError("brightness must be between 0 and 100")
        return replace(self, brightness=value)

    def to_payload(self, canvas: int) -> bytes:
        return bytes(
            [
                HID_SET_EFFECT,
                HID_EFFECT_CH_PARAM,
                canvas,
                self.mode,
                self.brightness,
                self.step,
                self.size,
                self.canvas_channel_count,
                self.vmap_process,
                self.delay,
                *self.color_1,
                *self.color_2,
                *self.color_3,
            ]
        )


def parse_general_config(response: bytes | list[int]) -> GeneralConfig:
    if len(response) < 19:
        raise ValueError("general-config response is too short")
    return GeneralConfig(
        mode=int(response[3]),
        brightness=int(response[4]),
        step=int(response[5]),
        size=int(response[6]),
        canvas_channel_count=int(response[7]),
        vmap_process=int(response[8]),
        delay=int(response[9]),
        color_1=tuple(int(value) for value in response[10:13]),  # type: ignore[arg-type]
        color_2=tuple(int(value) for value in response[13:16]),  # type: ignore[arg-type]
        color_3=tuple(int(value) for value in response[16:19]),  # type: ignore[arg-type]
    )


class HidTransport:
    def __init__(self, path: bytes | str) -> None:
        import hid

        self._device = hid.device()
        self._device.open_path(path)

    def write(self, report: bytes) -> None:
        written = self._device.write(report)
        if written < 0:
            raise OSError("HID write failed")

    def read(self, length: int, timeout_ms: int = READ_TIMEOUT_MS) -> bytes:
        for attempt in range(3):
            data = self._device.read(length, timeout_ms=timeout_ms)
            if data:
                return bytes(data)
            if attempt < 2:
                import time

                time.sleep(0.005)
        raise TimeoutError("Nollie controller did not respond")

    def close(self) -> None:
        self._device.close()


class NollieController:
    def __init__(self, device: Any, transport: HidTransport | None = None) -> None:
        self.device = device
        self.identity = ControllerId(device.model, device.serial or device.path_text)
        self._transport = transport or HidTransport(device.path)
        self._configs: list[GeneralConfig] = []

    def _request(self, payload: list[int]) -> bytes:
        self._transport.write(encode_report(payload, self.device.tx_len))
        return self._transport.read(self.device.rx_len)

    async def read_standby_brightness(self) -> tuple[int, ...]:
        response = await asyncio.to_thread(
            self._request,
            [HID_GET_EFFECT, HID_EFFECT_CANVAS_LEN],
        )
        canvas_count = int(response[0])
        if not 1 <= canvas_count <= self.device.channel_count:
            raise ValueError(f"invalid canvas count: {canvas_count}")
        configs: list[GeneralConfig] = []
        for canvas in range(canvas_count):
            response = await asyncio.to_thread(
                self._request,
                [HID_GET_EFFECT, HID_EFFECT_CH_PARAM, canvas],
            )
            configs.append(parse_general_config(response))
        self._configs = configs
        return tuple(config.brightness for config in configs)

    async def write_standby_brightness(self, values: tuple[int, ...]) -> None:
        if len(values) != len(self._configs):
            await self.read_standby_brightness()
        if len(values) != len(self._configs):
            raise ValueError("brightness count does not match controller canvas count")
        for canvas, (config, brightness) in enumerate(zip(self._configs, values, strict=True)):
            updated = config.with_brightness(brightness)
            await asyncio.to_thread(
                self._transport.write,
                encode_report(updated.to_payload(canvas), self.device.tx_len),
            )
            self._configs[canvas] = updated

    def close(self) -> None:
        self._transport.close()


class NollieControllerProtocol(Protocol):
    identity: ControllerId

    async def read_standby_brightness(self) -> tuple[int, ...]: ...

    async def write_standby_brightness(self, values: tuple[int, ...]) -> None: ...


class NollieLightingTarget:
    def __init__(self, controller: NollieControllerProtocol) -> None:
        self.controller = controller
        self.identity = TargetIdentity("nollie", controller.identity.key)

    async def snapshot(self) -> dict[str, object]:
        try:
            canvases = await self.controller.read_standby_brightness()
        except ValueError as exc:
            raise LightingError(str(exc)) from exc
        return {"canvases": list(canvases)}

    async def blackout(self, snapshot: dict[str, object]) -> None:
        canvases = self._canvases(snapshot)
        try:
            await self.controller.write_standby_brightness(tuple(0 for _ in canvases))
        except ValueError as exc:
            raise LightingError(str(exc)) from exc

    async def restore(self, snapshot: dict[str, object]) -> None:
        try:
            await self.controller.write_standby_brightness(self._canvases(snapshot))
        except ValueError as exc:
            raise LightingError(str(exc)) from exc

    def should_blackout(self, snapshot: dict[str, object]) -> bool:
        canvases = self._canvases(snapshot, allow_empty=True)
        return bool(canvases) and any(canvases)

    @staticmethod
    def _canvases(
        snapshot: dict[str, object],
        *,
        allow_empty: bool = False,
    ) -> tuple[int, ...]:
        canvases = snapshot.get("canvases")
        if not isinstance(canvases, list) or (not allow_empty and not canvases):
            raise LightingError("Nollie snapshot must contain a non-empty canvas list")
        if any(type(value) is not int or not 0 <= value <= 100 for value in canvases):
            raise LightingError(
                "Nollie canvas brightness must be an integer between 0 and 100"
            )
        return tuple(canvases)
