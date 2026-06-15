from pathlib import Path

import pytest

from magical_girl_glow_down.main import app_data_dir, build_parser


def test_cli_parses_simulation_options() -> None:
    args = build_parser().parse_args(["--simulate", "--cycles", "2", "--idle-seconds", "0.1"])
    assert args.simulate is True
    assert args.cycles == 2
    assert args.idle_seconds == 0.1
    assert build_parser().prog == "magical-girl-glow-down"


def test_cli_parses_gigabyte_probe() -> None:
    args = build_parser().parse_args(["--gigabyte-probe"])

    assert args.gigabyte_probe is True


def test_cli_parses_gigabyte_snapshot() -> None:
    args = build_parser().parse_args(["--gigabyte-snapshot"])

    assert args.gigabyte_snapshot is True


def test_cli_parses_gigabyte_test_all_with_restore_delay() -> None:
    args = build_parser().parse_args(["--gigabyte-test-all", "--restore-after", "5"])

    assert args.gigabyte_test_all is True
    assert args.restore_after == 5


def test_app_data_dir_uses_final_product_directory(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    result = app_data_dir()

    assert result == tmp_path / "MagicalGirlGlowDown"


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", "0", "-1"])
def test_idle_seconds_cli_rejects_invalid_values(value: str) -> None:
    import pytest
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--simulate", "--idle-seconds", value])

