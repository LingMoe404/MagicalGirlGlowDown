v0.1.0 - ✨ 魔法少女·静谧霓虹 (Magical Girl Glow Down) v0.1.0 - 始动 (Genesis) | Windows 待机灯效管理守护者

> **"让霓虹静静入眠，在触碰时再次苏醒。"**

经过无数个夜晚的炼成与调试，**魔法少女·静谧霓虹 (Magical Girl Glow Down)** 的初号机终于正式与各位适格者见面了！这是一款常驻 Windows 系统托盘的 RGB 待机管理工具。它通过无感监听键盘、鼠标与各种游戏手柄活动，在系统持续空闲后熄灭设备灯光，并在您的指尖再次触碰时瞬间唤醒、完美恢复原有的华丽色彩；同时具备智能避让机制，与官方/第三方控制软件和谐共存，默默守护你的桌面电竞美学。

> [!WARNING]
> **⚠️ 契约限制与兼容性声明 (Hardware Compatibility Warning)**
> 本工具**并非通用 RGB 软件**！请勿在未适配的硬件环境中使用。
> * **仅支持 Nollie 控制器**：不支持 Corsair、Razer、联力等其他品牌的 RGB 控制器。
> * **仅支持已验证的技嘉主板**：目前仅针对 `X870E AORUS MASTER X3D ICE` 完成了区域白名单匹配和实机测试。其它主板型号默认禁止写入，以防误写入导致硬件异常。


## 🎉 核心术式 (Highlights)

*   **⌨️ 全局空闲监听**: 同时监听键盘、鼠标、XInput、WinMM 与 Raw Input 游戏手柄，空闲自动进入待机（默认 30 秒）。
*   **🌈 Nollie 深度控制**: 深度适配 Nollie 系列控制器（Nollie1/8/16/32, Prism8, G857D 应用模式），通过 HIDAPI 接口安全读写。
*   **🖥️ 技嘉主板实机验证**: 已在 `X870E AORUS MASTER X3D ICE` 主板上完成实机验证，完美控制板载 Logo、装甲灯、5V ARGB 接口及 12V RGB 接口。
*   **🛡️ 软件共存守护**: 
    *   开启 `NollieRGB.exe` 时，自动释放 HID 设备并暂停控制。
    *   开启 GCC (`Gigabyte Control Center`) 时，仅暂停主板灯效控制，GCC 关闭后自动接管并同步灯效。
*   **🚀 无痛开机启动**: 通过最高权限的 Windows 计划任务运行，仅在首次启用时请求一次管理员权限，之后登录再无 UAC 弹窗打扰。

## 🛠️ 功能特性 (Features)

*   [x] **无感空闲检测**: 键盘/鼠标/XInput/WinMM/Raw Input 游戏手柄多维度精确计时。
*   [x] **无损灯效恢复**: 熄灯前自动保存当前亮度或完整色彩 JSON 配置，唤醒时原样恢复，避免重新套用固定预设。
*   [x] **防冲突避让**: 实时检测竞品/官方控制软件运行状态，自动释放或重新接管硬件读写权。
*   [x] **异常自动保护**: 即使程序异常退出或强杀进程，在下一次启动时也会自动读取残留快照，还原初始灯光。
*   [x] **诊断调试命令行**: 内置丰富命令行参数，支持 `--simulate` 模拟运行、`--gigabyte-probe` 只读探测及 `--gigabyte-test-all` 硬件测试。

## ⚙️ 适格者要求 (Requirements)

*   **OS**: Windows 10 / 11 (推荐 Win11)
*   **Hardware (二选一或兼有)**:
    *   🔵 **Nollie**: 受支持的 Nollie USB HID 控制器（Nollie1 / Nollie8 / Nollie16 / Nollie32 / Prism8 / G857D 模式）。
    *   🟢 **Gigabyte**: 已安装 Gigabyte Control Center (GCC) 的受支持技嘉主板（如 `X870E AORUS MASTER X3D ICE`）。
*   **Python**: 3.12.10
*   **Privilege**: 技嘉控制和开机启动安装需要管理员权限（首次运行托盘时请求一次 UAC 提权）。

## 📥 部署指南 (Installation)

### 方式一：下载正式版 (推荐)

*   **安装包 (Setup)**: 下载本页面下方的 `MagicalGirlGlowDown-v0.1.0-Setup.exe`，双击运行并按提示完成安装。
*   **便携版 (Portable)**: 下载本页面下方的 `MagicalGirlGlowDown-v0.1.0-Portable.7z`，解压至任意目录，双击 `MagicalGirlGlowDown.exe` 即可直接运行。

### 方式二：源码运行 (Dev)

1.  **环境**: 安装 Python 3.12.10 与 `uv` 包管理器。
2.  **依赖**: 在项目根目录执行：
    ```powershell
    uv sync --all-groups
    ```
3.  **编译**: 编译独立的技嘉辅助客户端：
    ```powershell
    powershell -ExecutionPolicy Bypass -File .\scripts\build-helper.ps1
    ```
4.  **启动**: 执行 `uv run magical-girl-glow-down` 启动仪式。

## 🧪 验证范围 (Verification Scope)

*   键盘/鼠标/各类游戏手柄的空闲熄灯与唤醒恢复流程。
*   Nollie 控制器设备热插拔、状态机切换与 NollieRGB 避让。
*   技嘉主板板载 Logo、装甲灯、5V ARGB 及 12V RGB 接口的熄灯与快照恢复。
*   `MagicalGirlGlowDown` 计划任务开机自启的创建、运行与卸载。
*   命令行模式下的硬件只读探测与自动恢复测试。

## 🤖 致谢 (Credits)

本软件的诞生与进化离不开以下 AI 协作者与智能体平台的鼎力相助：
*   **OpenAI Codex**：作为初始共同开发 AI，参与核心方案设计、协议分析、代码实现、测试与文档整理。
*   **Google Gemini (via Antigravity 平台)**：作为持续优化与重构 AI，负责本次 C# 辅助进程常驻化、原生 Win32 进程扫描、节流优化、单元测试补充以及安全/故障诊断文档整理。

We would like to express our gratitude to the following AI collaborators and platforms:
*   **OpenAI Codex**: As the initial co-development AI, assisted with core architecture design, protocol analysis, code implementation, testing, and documentation.
*   **Google Gemini (via the Antigravity platform)**: As the continuous optimization AI, optimized the architecture (including C# helper process persistence, native Windows process monitoring, etc.), refactored code, expanded test coverage, and refined documentation.

---
*“观测者啊，哪怕深夜长眠，静谧霓虹也会在下一次触碰时为你再次亮起！”*
