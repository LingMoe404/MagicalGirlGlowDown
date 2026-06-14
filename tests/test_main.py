from nollie_rgb_idle.main import build_parser


def test_cli_parses_simulation_options() -> None:
    args = build_parser().parse_args(
        ["--simulate", "--cycles", "2", "--idle-seconds", "0.1"]
    )
    assert args.simulate is True
    assert args.cycles == 2
    assert args.idle_seconds == 0.1


def test_cli_parses_gigabyte_probe() -> None:
    args = build_parser().parse_args(["--gigabyte-probe"])

    assert args.gigabyte_probe is True
