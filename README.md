# 魔法少女·静谧霓虹 (MagicalGirlGlowDown) - Windows Edition

[English](README_EN.md)

![Version](https://img.shields.io/badge/version-0.1.0-FB7299?style=for-the-badge)
![AI Co-developed](https://img.shields.io/badge/AI_Co--developed-Codex_%7C_GPT_%7C_Antigravity_%7C_Gemini-8E75B2?style=for-the-badge)
![Platform](https://img.shields.io/badge/OS-Windows_10_%7C_11-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12.10-3776AB?style=for-the-badge&logo=python&logoColor=white)

> **“让霓虹静静入眠，在触碰时再次苏醒。”**
>
> 一款运行在 Windows 后台的 RGB 待机管理工具。它会监听键盘、鼠标与游戏手柄活动，在电脑持续无输入后自动熄灭灯光，并在下一次操作时恢复原有效果。<br>
> 支持 Nollie 系列控制器，以及经过实机验证的技嘉主板板载灯光、5V ARGB 与 12V RGB 接口；同时会主动避让 NollieRGB 和 Gigabyte Control Center，减少多个灯效程序争夺硬件的问题。<br>
> *Built with Python, PySide6, HIDAPI and .NET · AI-assisted with Codex, GPT, Antigravity & Gemini.*

> [!IMPORTANT]
> **⚠️ 硬件支持限制声明 (Hardware Compatibility Disclaimer)**
> * 本工具**非通用** RGB 控制软件。**不支持**海盗船 (Corsair)、雷蛇 (Razer)、华硕 (ASUS)、微星 (MSI)、华擎 (ASRock)、联力 (Lian Li) 等主流品牌的任意设备。
> * **仅支持**特定型号的 **Nollie 系列控制器**（通过 USB HID 直连）。
> * **仅支持**经过配置与验证的**技嘉 (Gigabyte) 主板**（当前仅验证并适配了 `X870E AORUS MASTER X3D ICE` 这一款型号，且必须安装 Gigabyte Control Center）。其他型号或品牌的设备均保持禁止写入以策安全。

---

## 核心功能

* **全局空闲检测**：同时监听键盘、鼠标、XInput、WinMM 与 Raw Input 游戏手柄，默认在 30 秒无输入后进入待机。
* **精确恢复灯效**：熄灯前保存当前亮度或完整灯效状态，检测到输入后恢复原值，而不是重新套用固定预设。
* **后台托盘运行**：常驻 Windows 系统托盘，无需一直打开主界面。
* **Nollie 控制器支持**：支持 Nollie1、Nollie8、Prism8、Nollie16、Nollie32 与 G857D 应用模式 HID 接口。
* **技嘉主板灯光支持**：可控制已验证主板的板载 Logo、装甲灯、5V ARGB 接口与 12V RGB 接口。
* **软件共存保护**：
  * 打开 `NollieRGB.exe` 时，自动恢复灯光、释放 HID 设备并暂停 Nollie 写入。
  * 打开 Gigabyte Control Center 时，仅暂停技嘉主板控制，Nollie 控制器继续正常工作。
  * GCC 关闭后重新探测硬件，并将 GCC 最后设置的效果作为新的恢复状态。
* **异常恢复**：待机熄灯时保存恢复数据，即使程序意外退出，也能在下次启动时尝试恢复。
* **开机启动**：通过最高权限的 Windows 计划任务启动，只在首次启用时请求一次管理员权限，之后登录不再弹出 UAC。

## 工作方式

```text
键盘 / 鼠标 / 游戏手柄输入
              |
              v
        重置空闲计时
              |
       30 秒持续无输入
              |
              v
      保存当前 RGB 状态
              |
              v
            熄灯
              |
       检测到任意新输入
              |
              v
       恢复保存的灯效
```

MagicalGirlGlowDown 不会修改主板 BIOS、固件、灯效校准数据或 GCC 持久化配置。技嘉控制仅调用本机已安装 GCC 的运行时组件，并对未知设备与未知接口采取拒绝写入策略。

## 硬件支持

### Nollie 控制器

当前设备目录包含：

| 系列 | 支持状态 |
| :--- | :--- |
| Nollie1 / Nollie8 / Nollie16 / Nollie32 | 支持 |
| Prism8 | 支持 |
| G857D 应用模式接口 | 支持 |
| Bootloader、旧固件接口与未知硬件版本 | 不写入 |

NollieRGB 原程序无需保持运行。当它启动时，MagicalGirlGlowDown 会主动交还设备控制权。

### 技嘉主板

以下能力已在 `X870E AORUS MASTER X3D ICE` 上完成实机验证：

* 主板 IO 装甲与 PCH 灯光
* 四组 5V ARGB 接口
* 一组 12V RGB 接口
* 待机熄灯与输入恢复
* GCC 打开时暂停控制，关闭后恢复接管

技嘉支持依赖本机安装的 Gigabyte Control Center。项目不会分发或内置技嘉 DLL，其他主板型号需要单独验证。

## 系统要求

* **操作系统**：Windows 10 或 Windows 11
* **Python**：3.12.10
* **Nollie 控制**：受支持的 Nollie USB HID 控制器
* **技嘉控制**：已安装 Gigabyte Control Center 的受支持技嘉主板
* **权限**：
  * Nollie 控制和模拟模式通常不需要管理员权限。
  * 技嘉灯光写入需要管理员权限，托盘程序会在启动时集中请求一次。
  * 启用或移除开机启动需要管理员权限，以管理最高权限计划任务。

## 下载

### 方式一：下载正式版 (推荐)

1. 前往 [**Releases 页面**](https://github.com/LingMoe404/MagicalGirlGlowDown/releases) 下载最新版本的发布包。
2. 按需选择其一：
   * `MagicalGirlGlowDown-v<版本号>-Portable.7z`：解压至任意目录后，直接运行即可。
   * `MagicalGirlGlowDown-v<版本号>-Setup.exe`：双击安装，首次运行会请求一次管理员权限用于创建开机自启任务，之后不再弹出 UAC 提示。

## 源码运行

项目使用 [uv](https://docs.astral.sh/uv/) 管理 Python 环境与依赖。

1. 克隆仓库：

   ```powershell
   git clone https://github.com/LingMoe404/MagicalGirlGlowDown.git
   cd MagicalGirlGlowDown
   ```

2. 同步环境：

   ```powershell
   uv sync --all-groups
   ```

3. 构建独立的技嘉辅助程序：

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\build-helper.ps1
   ```

4. 启动托盘程序：

   ```powershell
   uv run magical-girl-glow-down
   ```

## 常用命令

### 模拟运行

无需连接真实硬件即可验证空闲与恢复流程：

```powershell
uv run magical-girl-glow-down --simulate --cycles 1 --idle-seconds 0.1
```

### 开机启动

```powershell
# 启用当前用户开机启动
uv run magical-girl-glow-down --install-autostart

# 移除开机启动
uv run magical-girl-glow-down --remove-autostart
```

开机启动使用 Windows 任务计划程序，任务名称为：

```text
MagicalGirlGlowDown
```

### 技嘉硬件诊断

执行下列命令前请关闭 Gigabyte Control Center：

```powershell
# 只读探测
uv run magical-girl-glow-down --gigabyte-probe --debug

# 读取完整灯效状态
uv run magical-girl-glow-down --gigabyte-snapshot --debug

# 熄灭全部受支持区域，并在 5 秒后自动恢复
uv run magical-girl-glow-down --gigabyte-test-all --restore-after 5 --debug
```

## 开发与测试

```powershell
uv sync --all-groups
uv run pytest
uv run ruff check .
uv run mypy src
dotnet test helper/MagicalGirlGlowDown.GigabyteHelper.Tests -c Release -v minimal
```

协议分析记录请参阅 [Nollie 协议说明](docs/protocol-notes.md)，技嘉实机验证过程请参阅 [技嘉验证记录](docs/gigabyte-validation.md)。

## 安全与加固运行

为了确保以管理员权限运行时系统与硬件的安全性，本工具实施了以下加固设计：

1. **权限模型**：整个托盘程序及 C# 辅助进程均以管理员权限运行。
2. **打包版本边界**：打包的可执行文件（Packaged Build）会严格忽略任何 helper 或 GCC 环境变量重定向路径（如 `MAGICALGIRLGLOWDOWN_GIGABYTE_HELPER` 和 `MAGICALGIRLGLOWDOWN_GCC_ROOT`），仅加载程序自身目录内的辅助进程，且仅在固定的 `%ProgramFiles%\GIGABYTE\Control Center` 下探测和调用 GCC。
3. **源码运行环境**：源码模式下允许通过环境变量进行重定向，但每次使用重定向路径时都会在日志中输出管理员级覆盖路径的警告。
4. **受保护的存储与暂存区**：硬件恢复状态（`state.json`）和技嘉暂存目录移动至全局 `%ProgramData%\MagicalGirlGlowDown` 目录下。该目录在创建时会被剥夺除 `SYSTEM` 和 `Administrators` 组以外的一切写权限，并在每次启动时进行权限校验与重解析点（符号链接/连接点）防篡改校验，防范非特权进程进行提权或替换 staging DLL。
5. **便携版开机启动安全确认**：当使用便携版（即程序不在 `Program Files` 目录下）启用开机自启动时，UI 和命令行会弹出明确的替换/提权安全风险警告，需要用户手动确认才会继续。
6. **故障隔离与自愈**：
   * **待机快照留存**：如果 GCC 正在运行导致灯光恢复失败，快照会被标记为 `pending_restore` 并被安全留存，在 GCC 关闭后自动重试恢复，绝不因 handoff 冲突而丢失快照。
   * **后台服务故障手动重试**：当后台输入监听服务发生致命异常时，会优雅捕获并通知托盘菜单，显示“后台服务已失效”，允许用户在托盘菜单中手动点击“重试后台服务”以拉起新实例。

## 使用提醒

1. 首次使用前，建议先在 NollieRGB 或 GCC 中备份当前灯效配置。
2. 调试技嘉控制时请关闭 GCC，日常运行时程序会自动检测并避让 GCC。
3. 未列入白名单的 Nollie VID、PID、接口或未知技嘉设备不会被写入。
4. 如果程序在熄灯期间被强制结束，请重新启动程序以触发恢复流程。

## 关于作者

我是 **泠萌404**，一名喜欢折腾硬件、NAS 和灯光控制的普通上班族。

| 平台 | ID / 频道 | 链接 |
| :--- | :--- | :--- |
| Bilibili | **泠萌404** | [点击跳转](https://space.bilibili.com/136850) |
| YouTube | **泠萌404** | [点击跳转](https://www.youtube.com/@LingMoe404) |
| Douyin | **泠萌404** | [点击跳转](https://www.douyin.com/user/MS4wLjABAAAA8fYebaVF2xlczanlTvT-bVoRxLqNjp5Tr01pV8wM88Q) |

## 致谢

本项目离不开以下开源项目、运行时与开发工具：

* [Python](https://www.python.org/)：主要应用与后台服务运行时。
* [PySide6](https://doc.qt.io/qtforpython/)：系统托盘与桌面交互。
* [HIDAPI](https://github.com/libusb/hidapi)：Nollie USB HID 通信。
* [.NET](https://dotnet.microsoft.com/)：隔离运行技嘉灯光控制组件。
* [uv](https://docs.astral.sh/uv/)：Python 项目与依赖管理。
* **OpenAI Codex / GPT**：初始共同开发。
* **Google Antigravity / Gemini**：重构优化与开发辅助。

## 开发幕后

MagicalGirlGlowDown 是一个由 **泠萌404 主导，AI 协作开发的项目**：
* **初始开发**：OpenAI Codex / GPT 协作。
* **重构优化**：Google Antigravity / Gemini 智能体协作。

Copyright © 2026 泠萌404
