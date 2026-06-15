from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from .branding import APP_NAME
from .security_paths import is_protected_install_path

TASK_NAME = APP_NAME


def requires_portable_confirmation(
    executable: Path,
    roots: Sequence[Path] | None = None,
) -> bool:
    return not is_protected_install_path(executable, roots)



class TaskScheduler(Protocol):
    def create(self, command: str) -> None: ...

    def delete(self) -> None: ...

    def exists(self) -> bool: ...


class WindowsTaskScheduler:
    def create(self, command: str) -> None:
        result = self._run(
            "/Create",
            "/F",
            "/TN",
            TASK_NAME,
            "/SC",
            "ONLOGON",
            "/RL",
            "HIGHEST",
            "/IT",
            "/TR",
            command,
        )
        if result.returncode != 0:
            raise OSError(result.stderr.strip() or "Could not create the startup task")

    def delete(self) -> None:
        if not self.exists():
            return
        result = self._run("/Delete", "/F", "/TN", TASK_NAME)
        if result.returncode != 0:
            raise OSError(result.stderr.strip() or "Could not delete the startup task")

    def exists(self) -> bool:
        return self._run("/Query", "/TN", TASK_NAME).returncode == 0

    @staticmethod
    def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ("schtasks.exe", *arguments),
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=False,
        )


class AutostartManager:
    def __init__(self, scheduler: TaskScheduler, command: str) -> None:
        self.scheduler = scheduler
        self.command = command

    def enable(self) -> None:
        self.scheduler.create(self.command)

    def disable(self) -> None:
        self.scheduler.delete()

    def enabled(self) -> bool:
        return self.scheduler.exists()
