from unittest.mock import patch
import sys
from magical_girl_glow_down.i18n import get_system_language, t


def test_locale_language_detection() -> None:
    # 1. Test Simplified Chinese locales
    with patch("ctypes.windll.kernel32.GetUserDefaultLocaleName", return_value=5) as mock_locale:
        # mock create_unicode_buffer value
        with patch("ctypes.create_unicode_buffer") as mock_buf:
            mock_buf.return_value.value = "zh-CN"
            assert get_system_language() == "zh_CN"

            mock_buf.return_value.value = "zh-SG"
            assert get_system_language() == "zh_CN"

            mock_buf.return_value.value = "zh-MY"
            assert get_system_language() == "zh_CN"

            mock_buf.return_value.value = "zh-Hans-CN"
            assert get_system_language() == "zh_CN"

    # 2. Test Traditional Chinese locales
    with patch("ctypes.windll.kernel32.GetUserDefaultLocaleName", return_value=5):
        with patch("ctypes.create_unicode_buffer") as mock_buf:
            mock_buf.return_value.value = "zh-TW"
            assert get_system_language() == "zh_TW"

            mock_buf.return_value.value = "zh-HK"
            assert get_system_language() == "zh_TW"

            mock_buf.return_value.value = "zh-MO"
            assert get_system_language() == "zh_TW"

            mock_buf.return_value.value = "zh-Hant-TW"
            assert get_system_language() == "zh_TW"

    # 3. Test other locales (fallback to English)
    with patch("ctypes.windll.kernel32.GetUserDefaultLocaleName", return_value=5):
        with patch("ctypes.create_unicode_buffer") as mock_buf:
            mock_buf.return_value.value = "en-US"
            assert get_system_language() == "en"

            mock_buf.return_value.value = "ja-JP"
            assert get_system_language() == "en"

            mock_buf.return_value.value = "fr-FR"
            assert get_system_language() == "en"


def test_translation_lookups() -> None:
    # Verify lookup and interpolation fallback logic
    # Since we imported t, we mock the CURRENT_LANG and LANG_DATA inside the module for testing
    with patch("magical_girl_glow_down.i18n.LANG_DATA", {"starting": "啟動中...", "exit": "退出", "autostart_failed_msg": "錯誤: {error}"}):
        assert t("starting") == "啟動中..."
        assert t("exit") == "退出"
        assert t("autostart_failed_msg", error="Access Denied") == "錯誤: Access Denied"
        
        # Test fallback to English key when missing in target lang data
        assert t("restore_now") == "Restore lighting now"
