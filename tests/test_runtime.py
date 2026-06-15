import builtins
import sys
from unittest.mock import patch

from magical_girl_glow_down.runtime import build_runtime_command, is_compiled, runtime_command


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


def test_is_compiled_detection() -> None:
    # 1. Test standard dev environment
    with patch("sys.executable", "C:\\Python312\\python.exe"):
        if hasattr(sys, "frozen"):
            delattr(sys, "frozen")
        if hasattr(builtins, "__compiled__"):
            delattr(builtins, "__compiled__")
        assert not is_compiled()

    # 2. Test pyinstaller environment
    with patch("sys.executable", "C:\\Python312\\python.exe"), \
         patch("sys.frozen", True, create=True):
        assert is_compiled()

    # 3. Test Nuitka environment
    with patch("sys.executable", "C:\\Python312\\python.exe"), \
         patch("builtins.__compiled__", True, create=True):
        assert is_compiled()

    # 4. Test binary name detection
    with patch("sys.executable", "C:\\Program Files\\MagicalGirlGlowDown\\MagicalGirlGlowDown.exe"):
        if hasattr(sys, "frozen"):
            delattr(sys, "frozen")
        if hasattr(builtins, "__compiled__"):
            delattr(builtins, "__compiled__")
        assert is_compiled()


def test_runtime_command_mitigates_nuitka_virtual_python() -> None:
    # Simulate a compiled environment where sys.executable points to python.exe, 
    # but MagicalGirlGlowDown.exe exists in the same folder.
    with patch("magical_girl_glow_down.runtime.is_compiled", return_value=True), \
         patch("sys.executable", "C:\\Program Files\\MagicalGirlGlowDown\\python.exe"), \
         patch("os.path.exists", return_value=True):
        cmd = runtime_command(("--debug",))
        assert cmd == ("C:\\Program Files\\MagicalGirlGlowDown\\MagicalGirlGlowDown.exe", "--debug")

