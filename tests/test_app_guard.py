from magical_girl_glow_down.app_guard import is_gcc_running, is_original_app_running


def test_process_guard_is_case_insensitive() -> None:
    assert is_original_app_running(["explorer.exe", "NOLLIERGB.EXE"])
    assert not is_original_app_running(["explorer.exe"])


def test_gcc_guard_is_case_insensitive() -> None:
    assert is_gcc_running(["explorer.exe", "GCC.EXE"])
    assert not is_gcc_running(["explorer.exe"])
