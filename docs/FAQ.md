# 🛠️ 常见问题 (FAQ)

[← 返回主页 (Back to README)](../README.md)

## ❓ 常见问题 (FAQ)

**Q: 为什么启动时提示需要管理员权限（或弹出 UAC 提权提示）？**  
A: 技嘉主板的控制依赖本机安装的 Gigabyte Control Center (GCC) 运行时组件，读取或写入主板硬件需要系统管理员权限。因此软件启动或配置开机启动项时，需要请求 UAC 提权。

**Q: 如何让它开机自启动，而不需要每次登录都弹出 UAC 确认？**  
A: 本软件内置了基于 Windows 任务计划程序 (Task Scheduler) 的自启动机制。您可以在系统托盘的右键菜单中勾选“开机启动”（或在命令行中运行 `uv run magical-girl-glow-down --install-autostart`），它会以系统最高权限在您登录时自动运行，之后每次登录都不会再弹出 UAC 提示。

**Q: 为什么我的技嘉主板灯光无法控制，或者提示 unsupported？**  
A: 为了保障您的硬件安全，本项目对技嘉主板采取了**白名单安全机制**。目前仅适配并验证了 `X870E AORUS MASTER X3D ICE` 这一款主板。其他主板型号在进行手动验证前，默认是拒绝写入的，以防写入未知地址导致主板固件或硬件发生异常。如果您想尝试适配自己的主板，可以关闭 GCC 后运行 `uv run magical-girl-glow-down --gigabyte-probe --debug` 进行只读探测，并在 GitHub 提交 Issue 提供日志与配置文件。

**Q: 开启官方灯控软件（如 NollieRGB.exe 或 GCC.exe）时会发生什么？会有冲突吗？**  
A: 工具内置了**防冲突避让机制**：
*   当检测到 `NollieRGB.exe` 运行时，本工具会自动暂停 Nollie 控制器的写入，释放 USB HID 设备，将控制权完全交还给官方软件。
*   当检测到 `GCC.exe` 运行时，会仅暂停技嘉主板的灯效控制，避免与 GCC 发生硬件争抢。
*   当官方软件关闭后，本工具会自动重新接管设备，并同步官方软件最后设置的灯光作为恢复状态。

**Q: 怎么快速测试熄灯和恢复功能是否正常，而不需要傻等 30 秒？**  
A: 您可以使用命令行下的**模拟运行模式**：
```powershell
uv run magical-girl-glow-down --simulate --cycles 1 --idle-seconds 0.1
```
或者使用技嘉硬件诊断命令（运行前请关闭 GCC）：
```powershell
uv run magical-girl-glow-down --gigabyte-test-all --restore-after 5 --debug
```
这会使已验证的主板区域熄灭，并在 5 秒后自动恢复其原本灯效。

**Q: 如果软件在熄灯期间被强制结束，灯光没有恢复怎么办？**  
A: 本工具具备**异常自愈机制**。熄灯前会自动在本地写入一份灯光状态恢复快照。如果在熄灯期间程序意外崩溃或被强杀，您只需再次启动本程序，它在初始化时会自动检测并读取残留的快照数据，将灯效还原。

---

# 🛠️ FAQ (English)

← Back to README

## ❓ Frequently Asked Questions (FAQ)

**Q: Why does the software prompt for administrator privileges (UAC elevation) on startup?**  
A: Gigabyte motherboard control relies on the runtime components of the locally installed Gigabyte Control Center (GCC). Reading or writing to the motherboard hardware requires administrator privileges. Therefore, the app requests UAC elevation during startup or when configuring autostart.

**Q: How can I set it to run on startup without triggering a UAC prompt every time?**  
A: The software features a built-in autostart mechanism based on the Windows Task Scheduler. You can check "Start on Boot" in the system tray context menu (or run `uv run magical-girl-glow-down --install-autostart` via CLI). It registers a task with highest privileges that runs on user login without prompting for UAC.

**Q: Why is my Gigabyte motherboard lighting not working, or showing "unsupported"?**  
A: To protect your hardware, this project implements a **whitelist safety mechanism** for Gigabyte motherboards. Currently, only the `X870E AORUS MASTER X3D ICE` is validated and mapped. Other motherboard models are write-disabled by default to prevent writing to unknown addresses that could cause firmware or hardware issues. If you want to adapt your motherboard, close GCC and run `uv run magical-girl-glow-down --gigabyte-probe --debug` to perform a read-only probe, and provide the logs in a GitHub Issue.

**Q: What happens if I open official lighting software (like NollieRGB.exe or GCC.exe)? Will there be conflicts?**  
A: The tool features built-in **conflict avoidance**:
*   If `NollieRGB.exe` is detected running, the tool pauses writing to Nollie controllers, releases the USB HID device, and yields full control to the official app.
*   If `GCC.exe` is detected running, it only pauses Gigabyte motherboard controls, preventing conflicts with GCC's hardware writes.
*   Once these official apps are closed, the tool automatically re-acquires control and syncs the last active lighting state set by them.

**Q: How can I quickly test the blackout and restore functions without waiting for 30 seconds?**  
A: You can use the **simulation mode** via CLI:
```powershell
uv run magical-girl-glow-down --simulate --cycles 1 --idle-seconds 0.1
```
Or use the Gigabyte hardware test command (ensure GCC is closed before running):
```powershell
uv run magical-girl-glow-down --gigabyte-test-all --restore-after 5 --debug
```
This turns off validated motherboard zones and restores their original effects after 5 seconds.

**Q: What if the software is force-closed during blackout, leaving the lights off?**  
A: The tool features an **auto-recovery mechanism**. Before blacking out, it saves a snapshot of the active lighting state. If the app crashes or is killed during blackout, simply start the app again. It will detect the snapshot on startup and restore the lights.
