from __future__ import annotations

from magical_girl_glow_down.simulator import run_simulation


async def test_simulator_dims_and_restores_multiple_controllers(tmp_path) -> None:
    result = await run_simulation(tmp_path, idle_seconds=0.001, cycles=1, sleep=lambda _: None)
    assert result.dimmed == ((0, 0), (0,))
    assert result.restored == ((30, 80), (55,))
