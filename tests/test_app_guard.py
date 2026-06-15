from unittest.mock import patch

from magical_girl_glow_down.app_guard import (
    is_gcc_running,
    is_original_app_running,
    is_process_running,
)


def test_process_guard_is_case_insensitive() -> None:
    assert is_original_app_running(["explorer.exe", "NOLLIERGB.EXE"])
    assert not is_original_app_running(["explorer.exe"])


def test_gcc_guard_is_case_insensitive() -> None:
    assert is_gcc_running(["explorer.exe", "GCC.EXE"])
    assert not is_gcc_running(["explorer.exe"])


def test_is_process_running_real() -> None:
    # explorer.exe is standard on Windows
    assert is_process_running("explorer.exe")
    assert not is_process_running("nonexistent_process_123456.exe")


def test_parameterless_app_guard() -> None:
    # These should run without error using the ctypes implementation
    # (Since these programs are probably not running on the test machine, they will return False,
    # but we can verify the functions execute without throwing exceptions)
    assert isinstance(is_original_app_running(), bool)
    assert isinstance(is_gcc_running(), bool)


def test_is_process_running_mocked() -> None:
    with patch("ctypes.byref", lambda x: x), \
         patch("ctypes.windll.kernel32.CreateToolhelp32Snapshot") as mock_snapshot, \
         patch("ctypes.windll.kernel32.Process32FirstW") as mock_first, \
         patch("ctypes.windll.kernel32.Process32NextW") as mock_next, \
         patch("ctypes.windll.kernel32.CloseHandle") as mock_close:

        mock_snapshot.return_value = 123

        def side_effect_first(h, pe):
            pe.szExeFile = "MockProcess.exe"
            return True

        mock_first.side_effect = side_effect_first

        def side_effect_next(h, pe):
            pe.szExeFile = "AnotherProcess.exe"
            # Return True first time, then False to terminate loop
            if not hasattr(side_effect_next, "called"):
                side_effect_next.called = True
                return True
            return False

        mock_next.side_effect = side_effect_next

        # Check matching
        assert is_process_running("mockprocess.exe")
        assert is_process_running("anotherprocess.exe")
        assert not is_process_running("nonexistent.exe")

        # Verify CloseHandle was called
        assert mock_close.call_count > 0
