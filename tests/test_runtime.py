from magical_girl_glow_down.runtime import build_runtime_command


def test_source_runtime_command_uses_python_module() -> None:
    assert build_runtime_command(
        "python.exe",
        ("--debug",),
        compiled=False,
    ) == (
        "python.exe",
        "-m",
        "magical_girl_glow_down.main",
        "--debug",
    )


def test_compiled_runtime_command_executes_application_directly() -> None:
    assert build_runtime_command(
        "MagicalGirlGlowDown.exe",
        ("--debug",),
        compiled=True,
    ) == (
        "MagicalGirlGlowDown.exe",
        "--debug",
    )
