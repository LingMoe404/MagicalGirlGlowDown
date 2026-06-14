from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest

from magical_girl_glow_down.gigabyte import (
    GigabyteError,
    GigabyteHelperClient,
    GigabyteLightingTarget,
)
from magical_girl_glow_down.lighting import TargetIdentity


def _write_helper(path: Path, response: dict[str, object]) -> tuple[str, ...]:
    path.write_text(
        "import json, sys\n"
        "request = json.loads(sys.stdin.readline())\n"
        f"response = {response!r}\n"
        "response['requestId'] = request['requestId']\n"
        "print(json.dumps(response), flush=True)\n",
        encoding="utf-8",
    )
    return (sys.executable, str(path))


async def test_helper_process_starts_without_a_console_window(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeProcess:
        returncode = 0

        async def communicate(self, encoded: bytes) -> tuple[bytes, bytes]:
            request = json.loads(encoded)
            response = {
                "schema": 1,
                "requestId": request["requestId"],
                "ok": True,
                "result": {"boardFingerprint": "board-A", "zones": []},
                "error": None,
            }
            return json.dumps(response).encode(), b""

    async def fake_create_subprocess_exec(*command, **options):
        captured["command"] = command
        captured["options"] = options
        return FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    await GigabyteHelperClient(("helper.exe",)).probe()

    assert captured["options"]["creationflags"] == subprocess.CREATE_NO_WINDOW


async def test_probe_parses_supported_zones(tmp_path: Path) -> None:
    command = _write_helper(
        tmp_path / "helper.py",
        {
            "schema": 1,
            "requestId": "",
            "ok": True,
            "result": {
                "boardFingerprint": "board-A",
                "zones": [
                    {"id": "logo", "category": "onboard", "name": "Logo"},
                    {"id": "d-led-1", "category": "argb5v", "name": "D_LED1"},
                    {"id": "led-c-1", "category": "rgb12v", "name": "LED_C1"},
                ],
            },
            "error": None,
        },
    )

    probe = await GigabyteHelperClient(command).probe()

    assert probe.board_fingerprint == "board-A"
    assert [zone.category for zone in probe.zones] == [
        "onboard",
        "argb5v",
        "rgb12v",
    ]


async def test_timeout_becomes_backend_error(tmp_path: Path) -> None:
    helper = tmp_path / "hang.py"
    helper.write_text("import time\ntime.sleep(60)\n", encoding="utf-8")
    client = GigabyteHelperClient((sys.executable, str(helper)), timeout=0.01)

    with pytest.raises(GigabyteError, match="timed out"):
        await client.probe()


async def test_structured_helper_error_is_raised(tmp_path: Path) -> None:
    command = _write_helper(
        tmp_path / "error.py",
        {
            "schema": 1,
            "requestId": "",
            "ok": False,
            "result": None,
            "error": {"code": "board_mismatch", "message": "wrong board"},
        },
    )

    with pytest.raises(GigabyteError, match="board_mismatch.*wrong board"):
        await GigabyteHelperClient(command).probe()


async def test_lighting_target_forwards_snapshot_blackout_and_restore(
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "requests.jsonl"
    helper = tmp_path / "recording.py"
    helper.write_text(
        "import json, sys\n"
        "request = json.loads(sys.stdin.readline())\n"
        f"open({str(log_path)!r}, 'a', encoding='utf-8').write(json.dumps(request) + '\\n')\n"
        "result = {'boardFingerprint': 'board-A', 'zones': [{'id': 'logo', "
        "'brightness': 80}]} if request['operation'] == 'snapshot' else {'applied': True}\n"
        "print(json.dumps({'schema': 1, 'requestId': request['requestId'], "
        "'ok': True, 'result': result, 'error': None}), flush=True)\n",
        encoding="utf-8",
    )
    client = GigabyteHelperClient((sys.executable, str(helper)))
    target = GigabyteLightingTarget(client, "board-A", ("logo",))

    snapshot = await target.snapshot()
    await target.blackout(snapshot)
    await target.restore(snapshot)

    assert target.identity == TargetIdentity("gigabyte", "board-A")
    operations = [
        json.loads(line)["operation"] for line in log_path.read_text(encoding="utf-8").splitlines()
    ]
    assert operations == ["snapshot", "blackout", "restore"]
