from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .lighting import LightingError, TargetIdentity

log = logging.getLogger(__name__)
SUPPORTED_CATEGORIES = frozenset({"onboard", "argb5v", "rgb12v", "unsupported"})


class GigabyteError(LightingError):
    """A recoverable failure from the isolated Gigabyte helper."""


@dataclass(frozen=True, slots=True)
class GigabyteZone:
    id: str
    category: str
    name: str


@dataclass(frozen=True, slots=True)
class GigabyteProbe:
    board_fingerprint: str
    zones: tuple[GigabyteZone, ...]
    board: dict[str, object] | None = None
    assembly_versions: dict[str, str] | None = None


def find_helper_command() -> tuple[str, ...]:
    configured = os.getenv("MAGICALGIRLGLOWDOWN_GIGABYTE_HELPER")
    if configured:
        return (configured,)

    package_dir = Path(__file__).resolve().parent
    packaged = package_dir / "gigabyte_helper" / "MagicalGirlGlowDown.GigabyteHelper.exe"
    if packaged.exists():
        return (str(packaged),)

    project = (
        package_dir.parents[1]
        / "helper"
        / "MagicalGirlGlowDown.GigabyteHelper"
        / "MagicalGirlGlowDown.GigabyteHelper.csproj"
    )
    if project.exists():
        return ("dotnet", "run", "--project", str(project), "--")
    raise GigabyteError("Gigabyte helper executable was not found")


class GigabyteHelperClient:
    def __init__(
        self,
        command: Sequence[str] | None = None,
        *,
        timeout: float = 10.0,
    ) -> None:
        self.command = tuple(command or find_helper_command())
        self.timeout = timeout

    async def probe(self) -> GigabyteProbe:
        result = await self._request("probe")
        board = self._required_string(result, "boardFingerprint")
        raw_zones = result.get("zones")
        if not isinstance(raw_zones, list):
            raise GigabyteError("helper probe result has no zone list")
        zones: list[GigabyteZone] = []
        for raw_zone in raw_zones:
            if not isinstance(raw_zone, dict):
                raise GigabyteError("helper returned an invalid zone")
            zone_id = self._required_string(raw_zone, "id")
            category = self._required_string(raw_zone, "category")
            if category not in SUPPORTED_CATEGORIES:
                raise GigabyteError(f"helper returned unknown zone category: {category}")
            name = raw_zone.get("name", zone_id)
            if not isinstance(name, str):
                raise GigabyteError("helper returned an invalid zone name")
            zones.append(GigabyteZone(zone_id, category, name))
        raw_board = result.get("board")
        board_details = raw_board if isinstance(raw_board, dict) else None
        raw_versions = result.get("assemblyVersions")
        versions = (
            {str(key): str(value) for key, value in raw_versions.items()}
            if isinstance(raw_versions, dict)
            else None
        )
        return GigabyteProbe(board, tuple(zones), board_details, versions)

    async def snapshot(
        self,
        board_fingerprint: str,
        zones: tuple[str, ...],
    ) -> dict[str, object]:
        return await self._request(
            "snapshot",
            {"boardFingerprint": board_fingerprint, "zones": list(zones)},
        )

    async def blackout(
        self,
        board_fingerprint: str,
        snapshot: dict[str, object],
    ) -> None:
        await self._request(
            "blackout",
            {"boardFingerprint": board_fingerprint, "snapshot": snapshot},
        )

    async def restore(
        self,
        board_fingerprint: str,
        snapshot: dict[str, object],
    ) -> None:
        await self._request(
            "restore",
            {"boardFingerprint": board_fingerprint, "snapshot": snapshot},
        )

    async def _request(
        self,
        operation: str,
        payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        request_id = uuid.uuid4().hex
        request = {
            "schema": 1,
            "requestId": request_id,
            "operation": operation,
            "payload": payload,
        }
        try:
            process = await asyncio.create_subprocess_exec(
                *self.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            raise GigabyteError(f"could not start Gigabyte helper: {exc}") from exc

        encoded = (json.dumps(request, ensure_ascii=True) + "\n").encode()
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(encoded),
                timeout=self.timeout,
            )
        except TimeoutError as exc:
            process.kill()
            await process.wait()
            raise GigabyteError("Gigabyte helper timed out") from exc

        if stderr:
            log.debug("Gigabyte helper stderr: %s", stderr.decode(errors="replace").strip())
        if process.returncode != 0:
            raise GigabyteError(f"Gigabyte helper exited with code {process.returncode}")
        try:
            response: Any = json.loads(stdout.decode())
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GigabyteError("Gigabyte helper returned invalid JSON") from exc
        if not isinstance(response, dict):
            raise GigabyteError("Gigabyte helper response is not an object")
        if response.get("schema") != 1 or response.get("requestId") != request_id:
            raise GigabyteError("Gigabyte helper response identity mismatch")
        if response.get("ok") is not True:
            error = response.get("error")
            if not isinstance(error, dict):
                raise GigabyteError("Gigabyte helper returned an unspecified error")
            code = error.get("code", "unknown_error")
            message = error.get("message", "unknown helper error")
            raise GigabyteError(f"{code}: {message}")
        result = response.get("result")
        if not isinstance(result, dict):
            raise GigabyteError("Gigabyte helper result is not an object")
        return result

    @staticmethod
    def _required_string(value: dict[str, Any], key: str) -> str:
        result = value.get(key)
        if not isinstance(result, str) or not result:
            raise GigabyteError(f"helper result has invalid {key}")
        return result


class GigabyteLightingTarget:
    def __init__(
        self,
        client: GigabyteHelperClient,
        board_fingerprint: str,
        zones: tuple[str, ...],
    ) -> None:
        self.client = client
        self.board_fingerprint = board_fingerprint
        self.zones = zones
        self.identity = TargetIdentity("gigabyte", board_fingerprint)

    async def snapshot(self) -> dict[str, object]:
        return await self.client.snapshot(self.board_fingerprint, self.zones)

    async def blackout(self, snapshot: dict[str, object]) -> None:
        await self.client.blackout(self.board_fingerprint, snapshot)

    async def restore(self, snapshot: dict[str, object]) -> None:
        await self.client.restore(self.board_fingerprint, snapshot)
