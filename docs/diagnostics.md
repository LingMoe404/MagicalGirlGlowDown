# 🔍 诊断与调试指南 (Diagnostics & Troubleshooting)

[← 返回主页 (Back to README)](../README.md)

本指南旨在帮助适格者诊断和排查 **魔法少女·静谧霓虹 (Magical Girl Glow Down)** 运行过程中遇到的各类软硬件交互问题。

---

## 🛠️ 命令行诊断工具 (CLI Tools)

本程序内置了数个命令行诊断命令，允许在不开启托盘图形界面的情况下独立调试各模块：

### 1. 模拟运行模式 (Simulation Mode)
*   **指令**: 
    ```powershell
    uv run magical-girl-glow-down --simulate --cycles 1 --idle-seconds 0.1
    ```
*   **用途**: 在没有物理硬件或未提权的情况下验证全局空闲检测、计时器倒计时、进入待机、输入唤醒以及状态恢复的完整业务流。

### 2. 技嘉主板只读探测 (Gigabyte Probe)
*   **指令**: 
    ```powershell
    uv run magical-girl-glow-down --gigabyte-probe --debug
    ```
*   **用途**: 读取并输出 Windows BIOS 注册表中的主板名称、本地已安装 GCC 的 DLL 版本以及 `Profile-0.xml` 配置文件中记录的区域数。
*   **注意**: 该命令是以只读方式运行，**不会**初始化硬件控制器或修改任何灯光，也不需要管理员权限。

### 3. 主板快照截取 (Gigabyte Snapshot)
*   **指令**: 
    ```powershell
    uv run magical-girl-glow-down --gigabyte-snapshot --debug
    ```
*   **用途**: 尝试初始化技嘉硬件控制器，截取并输出当前所有灯光区域的颜色、速度、亮度及厂商专有 JSON 状态。
*   **注意**: 此命令需要管理员权限。

### 4. 技嘉黑屏唤醒测试 (Gigabyte Blackout Test)
*   **指令**: 
    ```powershell
    uv run magical-girl-glow-down --gigabyte-test-all --restore-after 5 --debug
    ```
*   **用途**: 立即将主板已验证的 7 个灯效区域设为黑色（熄灯），并在 5 秒后自动调用快照数据恢复灯效。
*   **注意**: 恢复延时范围必须在 `1` 到 `30` 秒之间。测试前请务必关闭官方 GCC 软件。

---

## ⚠️ 常见故障排除 (Troubleshooting)

### Q1: 运行技嘉控制命令行时，提示 C# 辅助进程（GigabyteHelper）错误或初始化失败
*   **原因 1**: 本项目没有内置技嘉的驱动或 DLL 文件，它依赖您系统上安装好的官方 **Gigabyte Control Center (GCC)**。如果未安装 GCC，或者 GCC 文件受损，辅助进程将无法运行。
*   **原因 2**: 没有以管理员权限运行命令行。技嘉官方 SDK 读取主板 ID 必须拥有提权。
*   **排查步骤**:
    1. 确保 GCC 在 Windows 中能正常调节灯光。
    2. 打开管理员权限的 PowerShell，尝试直接运行辅助可执行文件以捕获 C# 的底层异常：
       ```powershell
       .\src\magical_girl_glow_down\gigabyte_helper\MagicalGirlGlowDown.GigabyteHelper.exe probe
       ```

### Q2: 电脑已经没有操作了，但软件一直不进入待机熄灯状态
*   **原因 1**: 硬件输入设备干扰。某些具备“宏按键”的键盘/鼠标，或者存在“摇杆漂移”的外部游戏手柄（XInput / Raw Input）可能会在空闲时不断向 Windows 发送微小的模拟信号，从而频繁重置空闲计时器。
*   **原因 2**: 后台存在特定的音视频播放（通过 Windows 系统的休眠阻止 API ）。
*   **排查步骤**:
    1. 启动命令行版本并加入 `--debug` 参数：
       ```powershell
       uv run magical-girl-glow-down --debug
       ```
    2. 观察控制台输出日志，确认是在哪一个输入源（如 `RawInput`, `XInput`, `WinMM` 等）收到信号导致了 `[InputMonitor] Reset idle time`。
    3. 尝试拔掉对应的设备，或在代码中调整该输入源的监听级别。

### Q3: Nollie 控制器指示灯不熄灭，但软件显示已经进入待机
*   **原因**: Nollie 设备可能处于 Bootloader 烧录模式，或者其 USB PID/VID 不在标准白名单中。
*   **排查步骤**:
    1. 确认 Nollie 官方的 `NollieRGB` 软件是否能正常读写设备。
    2. 在设备管理器中检查 Nollie 控制器的 USB 硬件 ID，确认其 VID 是否为 `0483` 等标准白名单 ID。

---

# 🔍 Diagnostics & Troubleshooting (English)

← Back to README

This guide helps you troubleshoot hardware and software communication issues in **Magical Girl: Tranquil Neon (Magical Girl Glow Down)**.

## 🛠️ CLI Diagnostics

You can run diagnostics directly from the command line without opening the GUI:

### 1. Simulation Mode
```powershell
uv run magical-girl-glow-down --simulate --cycles 1 --idle-seconds 0.1
```
Tests the idle monitoring timer, standby transition, input detection, and state recovery flows without requiring physical hardware or elevated permissions.

### 2. Read-Only Motherboard Probe
```powershell
uv run magical-girl-glow-down --gigabyte-probe --debug
```
Queries the motherboard name from the registry, checks local GCC DLL versions, and counts profiles. Safe to run without Admin elevation.

### 3. Capture Motherboard Snapshot
```powershell
uv run magical-girl-glow-down --gigabyte-snapshot --debug
```
Initializes the motherboard controller and prints the current RGB color, speed, brightness, and raw state JSON. Requires Admin elevation.

### 4. Direct Blackout & Restore Test
```powershell
uv run magical-girl-glow-down --gigabyte-test-all --restore-after 5 --debug
```
Immediately blackouts all 7 validated zones and restores them after 5 seconds. Requires Admin elevation. Close GCC before running.

---

## ⚠️ Troubleshooting FAQ

### Q1: GigabyteHelper process fails to initialize or crashes
*   **Reason 1**: The helper process requires **Gigabyte Control Center (GCC)** to be installed locally to load its proprietary libraries.
*   **Reason 2**: The CLI session does not have Administrator privileges.
*   **Triage**:
    1. Confirm GCC can control your motherboard lights.
    2. Run the executable directly in an elevated PowerShell to capture the .NET exception:
       ```powershell
       .\src\magical_girl_glow_down\gigabyte_helper\MagicalGirlGlowDown.GigabyteHelper.exe probe
       ```

### Q2: The computer is idle, but the software never enters standby
*   **Reason 1**: Stick drift on gamepad controllers (XInput/Raw Input) or continuous polling by macro-enabled mice/keyboards resetting the timer.
*   **Triage**:
    1. Run the app in debug mode:
       ```powershell
       uv run magical-girl-glow-down --debug
       ```
    2. Monitor the logs to identify which device source (e.g. `RawInput`, `XInput`, `WinMM`) triggers the `[InputMonitor] Reset idle time` message.

### Q3: Nollie controllers do not turn off
*   **Reason**: The device is in bootloader mode, or its USB VID/PID is not whitelisted in `protocol.py`.
*   **Triage**: Ensure the official NollieRGB client works correctly with the device.
