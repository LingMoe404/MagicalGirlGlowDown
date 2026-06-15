import builtins
import ctypes
import sys
from typing import Any

TRANSLATIONS: dict[str, dict[str, str]] = {
    "zh_CN": {
        "starting": "启动中...",
        "pause": "暂停",
        "resume": "恢复",
        "paused": "暂停中",
        "running": "工作中",
        "idle": "待机中",
        "waiting_devices": "等待灯效设备",
        "paused_both_open": "暂停：GCC 和 NollieRGB 已打开",
        "paused_gcc_open": "技嘉暂停：GCC 已打开",
        "paused_nolliergb_open": "Nollie 暂停：NollieRGB 已打开",
        
        "restore_now": "立即恢复灯效",
        "set_timeout": "设置空闲超时...",
        "start_with_windows": "开机自动启动",
        "exit": "退出",
        "timeout_dialog_title": "设置空闲超时",
        "timeout_dialog_label": "空闲时间 (秒):",
        
        "autostart_failed_title": "设置开机启动失败",
        "autostart_failed_msg": "设置开机启动失败：\n{error}\n\n提示：此操作通常需要管理员权限。请尝试以管理员身份运行程序后重试。",
        "admin_needed": "MagicalGirlGlowDown 需要管理员权限以控制技嘉灯光。",
    },
    "zh_TW": {
        "starting": "啟動中...",
        "pause": "暫停",
        "resume": "恢復",
        "paused": "暫停中",
        "running": "工作中",
        "idle": "待機中",
        "waiting_devices": "等待燈效設備",
        "paused_both_open": "暫停：GCC 和 NollieRGB 已打開",
        "paused_gcc_open": "技嘉暫停：GCC 已打開",
        "paused_nolliergb_open": "Nollie 暫停：NollieRGB 已打開",
        
        "restore_now": "立即恢復燈效",
        "set_timeout": "設置空閒超時...",
        "start_with_windows": "開機自動啟動",
        "exit": "退出",
        "timeout_dialog_title": "設置空閒超時",
        "timeout_dialog_label": "空閒時間 (秒):",
        
        "autostart_failed_title": "設置開機啟動失敗",
        "autostart_failed_msg": "設置開機啟動失敗：\n{error}\n\n提示：此操作通常需要管理員權限。請嘗試以管理員身份運行程序後重試。",
        "admin_needed": "MagicalGirlGlowDown 需要管理員權限以控制技嘉燈光。",
    },
    "en": {
        "starting": "Starting...",
        "pause": "Pause",
        "resume": "Resume",
        "paused": "Paused",
        "running": "Running",
        "idle": "Dimmed",
        "waiting_devices": "Waiting for lighting devices",
        "paused_both_open": "Paused: GCC and NollieRGB are open",
        "paused_gcc_open": "Gigabyte paused: GCC is open",
        "paused_nolliergb_open": "Nollie paused: NollieRGB is open",
        
        "restore_now": "Restore lighting now",
        "set_timeout": "Set idle timeout...",
        "start_with_windows": "Start with Windows",
        "exit": "Exit",
        "timeout_dialog_title": "Set Idle Timeout",
        "timeout_dialog_label": "Idle timeout (seconds):",
        
        "autostart_failed_title": "Autostart Configuration Failed",
        "autostart_failed_msg": "Failed to configure autostart:\n{error}\n\nTip: This action usually requires administrator privileges. Please try running the application as administrator.",
        "admin_needed": "MagicalGirlGlowDown needs administrator permission for Gigabyte lighting.",
    }
}


def get_system_language() -> str:
    try:
        buf = ctypes.create_unicode_buffer(85)
        if ctypes.windll.kernel32.GetUserDefaultLocaleName(buf, 85) > 0:
            locale_name = buf.value.lower()
            # Simplified Chinese: zh-CN (PRC), zh-SG (Singapore), zh-MY (Malaysia), or contains "hans"
            if (
                locale_name.startswith("zh-cn")
                or locale_name.startswith("zh-sg")
                or locale_name.startswith("zh-my")
                or "hans" in locale_name
            ):
                return "zh_CN"
            # Traditional Chinese: zh-TW (Taiwan), zh-HK (Hong Kong), zh-MO (Macau), or contains "hant"
            elif (
                locale_name.startswith("zh-tw")
                or locale_name.startswith("zh-hk")
                or locale_name.startswith("zh-mo")
                or "hant" in locale_name
            ):
                return "zh_TW"
    except Exception:
        pass
    return "en"


CURRENT_LANG = get_system_language()
LANG_DATA = TRANSLATIONS[CURRENT_LANG]


def t(key: str, **kwargs: Any) -> str:
    text = LANG_DATA.get(key, TRANSLATIONS["en"].get(key, key))
    if kwargs:
        return text.format(**kwargs)
    return text
