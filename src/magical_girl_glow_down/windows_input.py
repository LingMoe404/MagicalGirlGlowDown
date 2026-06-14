from __future__ import annotations

import ctypes
import time
from ctypes import wintypes
from dataclasses import dataclass, field
from typing import Any


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


def keyboard_mouse_idle_seconds() -> float:
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(info)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        raise ctypes.WinError()
    elapsed_ms = (ctypes.windll.kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF
    return float(elapsed_ms) / 1000.0


def state_has_activity(
    previous: tuple[int, ...] | None,
    current: tuple[int, ...],
    dead_zone: int,
) -> bool:
    if previous is None:
        return True
    if previous[0] != current[0]:
        return True
    return any(
        abs(left - right) >= dead_zone
        for left, right in zip(previous[1:], current[1:], strict=True)
    )


class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", wintypes.WORD),
        ("bLeftTrigger", wintypes.BYTE),
        ("bRightTrigger", wintypes.BYTE),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


class XINPUT_STATE(ctypes.Structure):
    _fields_ = [("dwPacketNumber", wintypes.DWORD), ("Gamepad", XINPUT_GAMEPAD)]


class JOYINFOEX(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("dwXpos", wintypes.DWORD),
        ("dwYpos", wintypes.DWORD),
        ("dwZpos", wintypes.DWORD),
        ("dwRpos", wintypes.DWORD),
        ("dwUpos", wintypes.DWORD),
        ("dwVpos", wintypes.DWORD),
        ("dwButtons", wintypes.DWORD),
        ("dwButtonNumber", wintypes.DWORD),
        ("dwPOV", wintypes.DWORD),
        ("dwReserved1", wintypes.DWORD),
        ("dwReserved2", wintypes.DWORD),
    ]


def _load_xinput() -> Any | None:
    for name in ("xinput1_4", "xinput1_3", "xinput9_1_0"):
        try:
            return ctypes.WinDLL(name)
        except OSError:
            continue
    return None


@dataclass
class GameControllerMonitor:
    axis_dead_zone: int = 2048
    last_activity: float = field(default_factory=time.monotonic)
    _xinput: Any | None = field(default_factory=_load_xinput)
    _xinput_packets: dict[int, int] = field(default_factory=dict)
    _winmm_states: dict[int, tuple[int, ...]] = field(default_factory=dict)

    def record_raw_input(self) -> None:
        self.last_activity = time.monotonic()

    def poll(self) -> bool:
        active = self._poll_xinput() | self._poll_winmm()
        if active:
            self.last_activity = time.monotonic()
        return active

    def _poll_xinput(self) -> bool:
        if self._xinput is None:
            return False
        active = False
        for index in range(4):
            state = XINPUT_STATE()
            result = self._xinput.XInputGetState(index, ctypes.byref(state))
            if result != 0:
                self._xinput_packets.pop(index, None)
                continue
            packet = int(state.dwPacketNumber)
            previous = self._xinput_packets.get(index)
            self._xinput_packets[index] = packet
            active |= previous is not None and previous != packet
        return active

    def _poll_winmm(self) -> bool:
        winmm = ctypes.windll.winmm
        active = False
        for index in range(min(int(winmm.joyGetNumDevs()), 32)):
            info = JOYINFOEX()
            info.dwSize = ctypes.sizeof(info)
            info.dwFlags = 0xFF
            if winmm.joyGetPosEx(index, ctypes.byref(info)) != 0:
                self._winmm_states.pop(index, None)
                continue
            current = (
                int(info.dwButtons),
                int(info.dwXpos),
                int(info.dwYpos),
                int(info.dwZpos),
                int(info.dwRpos),
                int(info.dwUpos),
                int(info.dwVpos),
                int(info.dwPOV),
            )
            previous = self._winmm_states.get(index)
            self._winmm_states[index] = current
            if previous is not None and state_has_activity(
                previous,
                current,
                self.axis_dead_zone,
            ):
                active = True
        return active


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [
        ("usUsagePage", wintypes.USHORT),
        ("usUsage", wintypes.USHORT),
        ("dwFlags", wintypes.DWORD),
        ("hwndTarget", wintypes.HWND),
    ]


def register_game_controller_raw_input(hwnd: int) -> None:
    devices = (RAWINPUTDEVICE * 3)(
        RAWINPUTDEVICE(0x01, 0x04, 0x00000100, hwnd),
        RAWINPUTDEVICE(0x01, 0x05, 0x00000100, hwnd),
        RAWINPUTDEVICE(0x01, 0x08, 0x00000100, hwnd),
    )
    if not ctypes.windll.user32.RegisterRawInputDevices(
        devices,
        len(devices),
        ctypes.sizeof(RAWINPUTDEVICE),
    ):
        raise ctypes.WinError()
