from nollie_rgb_idle.app_guard import is_original_app_running


def test_process_guard_is_case_insensitive() -> None:
    assert is_original_app_running(["explorer.exe", "NOLLIERGB.EXE"])
    assert not is_original_app_running(["explorer.exe"])
