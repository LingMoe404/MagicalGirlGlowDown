import builtins
import os
import sys
from collections.abc import Sequence

from .branding import MODULE_ENTRY


def is_compiled() -> bool:
    if getattr(sys, "frozen", False):
        return True
    if hasattr(builtins, "__compiled__"):
        return True
    # If the base name of the executable does not contain "python",
    # it is almost certainly a packaged/compiled binary executable.
    if "python" not in os.path.basename(sys.executable).lower():
        return True
    return False


def build_runtime_command(
    executable: str,
    arguments: Sequence[str] = (),
    *,
    compiled: bool,
) -> tuple[str, ...]:
    if compiled:
        return (executable, *arguments)
    return (executable, "-m", MODULE_ENTRY, *arguments)


def runtime_command(arguments: Sequence[str] = ()) -> tuple[str, ...]:
    compiled = is_compiled()
    executable = sys.executable

    if compiled:
        # Under Nuitka standalone compilations, sys.executable might point to
        # a virtual/mock 'python.exe' next to the main binary for compatibility.
        # We need to map it back to the actual 'MagicalGirlGlowDown.exe' which exists.
        basename = os.path.basename(executable).lower()
        if "python" in basename:
            dir_name = os.path.dirname(executable)
            real_exe = os.path.join(dir_name, "MagicalGirlGlowDown.exe")
            if os.path.exists(real_exe):
                executable = real_exe

    return build_runtime_command(
        executable,
        arguments,
        compiled=compiled,
    )
