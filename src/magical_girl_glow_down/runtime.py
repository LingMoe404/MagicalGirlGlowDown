from __future__ import annotations

import sys
from collections.abc import Sequence

from .branding import MODULE_ENTRY


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
    return build_runtime_command(
        sys.executable,
        arguments,
        compiled="__compiled__" in globals(),
    )
