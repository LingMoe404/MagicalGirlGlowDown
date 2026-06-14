from __future__ import annotations

from typing import Protocol

from .branding import AUTOSTART_VALUE_NAME

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = AUTOSTART_VALUE_NAME


class Registry(Protocol):
    def set(self, name: str, value: str) -> None: ...

    def delete(self, name: str) -> None: ...

    def get(self, name: str) -> str | None: ...


class WindowsRunRegistry:
    def set(self, name: str, value: str) -> None:
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)

    def delete(self, name: str) -> None:
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                RUN_KEY,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.DeleteValue(key, name)
        except FileNotFoundError:
            pass

    def get(self, name: str) -> str | None:
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                return str(winreg.QueryValueEx(key, name)[0])
        except FileNotFoundError:
            return None


class AutostartManager:
    def __init__(self, registry: Registry, command: str) -> None:
        self.registry = registry
        self.command = command

    def enable(self) -> None:
        self.registry.set(VALUE_NAME, self.command)

    def disable(self) -> None:
        self.registry.delete(VALUE_NAME)

    def enabled(self) -> bool:
        return self.registry.get(VALUE_NAME) == self.command
