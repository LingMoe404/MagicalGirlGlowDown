# 魔法少女·静谧霓虹 (MagicalGirlGlowDown) - Windows Edition

![Version](https://img.shields.io/badge/version-0.1.0-FB7299?style=for-the-badge)
![AI Co-developed](https://img.shields.io/badge/AI_Co--developed-OpenAI_Codex-8E75B2?style=for-the-badge)
![Platform](https://img.shields.io/badge/OS-Windows_10_%7C_11-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12.10-3776AB?style=for-the-badge&logo=python&logoColor=white)

> **“让霓虹静静入眠，在触碰时再次苏醒。”**
>
> 一款运行在 Windows 后台的 RGB 待机管理工具。它会监听键盘、鼠标与游戏手柄活动，在电脑持续无输入后自动熄灭灯光，并在下一次操作时恢复原有效果。<br>
> 支持 Nollie 系列控制器，以及经过实机验证的技嘉主板板载灯光、5V ARGB 与 12V RGB 接口；同时会主动避让 NollieRGB 和 Gigabyte Control Center，减少多个灯效程序争夺硬件的问题。<br>
> *Built with Python, PySide6, HIDAPI and .NET · AI-assisted with OpenAI Codex.*

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
* **开机启动**：支持写入当前用户的 Windows 启动项，不需要管理员权限。

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
  * Nollie 控制、模拟模式和开机启动配置通常不需要管理员权限。
  * 技嘉灯光写入需要管理员权限，托盘程序会在启动时集中请求一次。

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

当前阶段暂不提供 Portable 压缩包与安装程序，请通过源码运行。

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

启动项位于：

```text
HKCU\Software\Microsoft\Windows\CurrentVersion\Run
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
* **OpenAI Codex**：参与方案设计、协议分析、代码实现、测试与文档整理。

## 开发幕后

MagicalGirlGlowDown 是一个由 **泠萌404 主导的 AI 辅助开发项目**。泠萌404负责产品方向、需求定义、硬件验证与最终决策；OpenAI Codex 协作参与架构设计、代码实现、调试、测试和文档整理。

Copyright © 2026 泠萌404
