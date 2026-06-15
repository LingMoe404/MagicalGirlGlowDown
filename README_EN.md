# Magical Girl: Tranquil Neon (MagicalGirlGlowDown) - Windows Edition

[简体中文](README.md)

![Version](https://img.shields.io/badge/version-0.1.0-FB7299?style=for-the-badge)
![AI Co-developed](https://img.shields.io/badge/AI_Co--developed-Codex_%7C_GPT_%7C_Antigravity_%7C_Gemini-8E75B2?style=for-the-badge)
![Platform](https://img.shields.io/badge/OS-Windows_10_%7C_11-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12.10-3776AB?style=for-the-badge&logo=python&logoColor=white)

> **"Let the neon drift quietly to sleep, then wake again at your touch."**
>
> A background RGB idle manager for Windows. It monitors keyboard, mouse, and
> game controller activity, turns the lighting off after a sustained period
> without input, and restores the original effects when activity resumes.<br>
> It supports Nollie controllers and validated Gigabyte motherboard lighting,
> including onboard zones, 5V ARGB headers, and 12V RGB headers. It also yields
> control to NollieRGB and Gigabyte Control Center to reduce hardware conflicts
> between lighting applications.<br>
> *Built with Python, PySide6, HIDAPI and .NET · AI-assisted with Codex, GPT, Antigravity & Gemini.*

> [!IMPORTANT]
> **⚠️ Hardware Compatibility Disclaimer**
> * This tool is **NOT a universal** RGB control software. It **DOES NOT support** arbitrary devices from Corsair, Razer, ASUS, MSI, ASRock, Lian Li, or other mainstream brands.
> * It **ONLY supports** specific models of **Nollie series controllers** (via direct USB HID connection).
> * It **ONLY supports** configured and validated **Gigabyte motherboards** (currently, only `X870E AORUS MASTER X3D ICE` is validated and mapped, requiring Gigabyte Control Center). All other motherboard models or brand devices are write-disabled for safety.

---

## Features

* **Global idle detection**: Monitors keyboard, mouse, XInput, WinMM, and Raw
  Input game controllers. The default idle timeout is 30 seconds.
* **Exact effect restoration**: Saves the current brightness or complete effect
  state before blackout, then restores the saved value instead of applying a
  fixed preset.
* **Background tray operation**: Runs from the Windows system tray without
  keeping a main window open.
* **Nollie controller support**: Supports Nollie1, Nollie8, Prism8, Nollie16,
  Nollie32, and G857D application-mode HID interfaces.
* **Gigabyte motherboard lighting support**: Controls validated onboard logos,
  armor lighting, 5V ARGB headers, and 12V RGB headers.
* **Application coexistence protection**:
  * When `NollieRGB.exe` opens, the app restores the lights, releases HID
    devices, and pauses Nollie writes.
  * When Gigabyte Control Center opens, only Gigabyte motherboard control is
    paused; Nollie controllers continue working.
  * After GCC closes, hardware is detected again and GCC's most recently saved
    effect becomes the new restoration state.
* **Crash recovery**: Saves restoration data during blackout so the next launch
  can attempt recovery after an unexpected exit.
* **Start with Windows**: Uses a highest-privilege Windows scheduled task. It
  requests administrator permission once when enabled, then starts at sign-in
  without another UAC prompt.

## How It Works

```text
Keyboard / mouse / game controller input
                    |
                    v
             Reset idle timer
                    |
        30 seconds without input
                    |
                    v
          Save current RGB state
                    |
                    v
                Blackout
                    |
            Any new input
                    |
                    v
          Restore saved effects
```

MagicalGirlGlowDown does not modify motherboard BIOS settings, firmware,
lighting calibration data, or persistent GCC configuration. Gigabyte control
uses only runtime components from the locally installed GCC and refuses writes
to unknown devices or interfaces.

## Hardware Support

### Nollie Controllers

The current device catalog includes:

| Series | Support |
| :--- | :--- |
| Nollie1 / Nollie8 / Nollie16 / Nollie32 | Supported |
| Prism8 | Supported |
| G857D application-mode interface | Supported |
| Bootloaders, legacy firmware interfaces, and unknown hardware revisions | Write-disabled |

The original NollieRGB application does not need to remain open. When it starts,
MagicalGirlGlowDown returns control of the device automatically.

### Gigabyte Motherboards

The following capabilities have been validated on
`X870E AORUS MASTER X3D ICE`:

* Motherboard I/O armor and PCH lighting
* Four 5V ARGB headers
* One 12V RGB header
* Idle blackout and input-triggered restoration
* Pausing control while GCC is open and resuming after it closes

Gigabyte support depends on a locally installed Gigabyte Control Center. This
project does not distribute or embed Gigabyte DLLs. Other motherboard models
require separate validation.

## Requirements

* **Operating system**: Windows 10 or Windows 11
* **Python**: 3.12.10
* **Nollie control**: A supported Nollie USB HID controller
* **Gigabyte control**: A supported Gigabyte motherboard with Gigabyte Control
  Center installed
* **Permissions**:
  * Nollie control and simulation mode usually do not require administrator
    permission.
  * Gigabyte lighting writes require administrator permission. The tray app
    requests elevation once during startup.
  * Enabling or removing startup requires administrator permission to manage
    the highest-privilege scheduled task.

## Downloads

### Method 1: Download Official Release (Recommended)

1. Go to the [**Releases Page**](https://github.com/LingMoe404/MagicalGirlGlowDown/releases) and download the latest release assets.
2. Choose whichever suits you best:
   * `MagicalGirlGlowDown-v<version>-Portable.7z`: unzip it to any directory and run it directly.
   * `MagicalGirlGlowDown-v<version>-Setup.exe`: run the installer, which requests administrator permission once during installation to create a sign-in task that does not prompt for UAC on subsequent startups.

## Running from Source

The project uses [uv](https://docs.astral.sh/uv/) to manage Python and its
dependencies.

1. Clone the repository:

   ```powershell
   git clone https://github.com/LingMoe404/MagicalGirlGlowDown.git
   cd MagicalGirlGlowDown
   ```

2. Synchronize the environment:

   ```powershell
   uv sync --all-groups
   ```

3. Build the standalone Gigabyte helper:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\build-helper.ps1
   ```

4. Start the tray application:

   ```powershell
   uv run magical-girl-glow-down
   ```

## Common Commands

### Simulation

Validate the idle and restoration flow without connecting real hardware:

```powershell
uv run magical-girl-glow-down --simulate --cycles 1 --idle-seconds 0.1
```

### Start with Windows

```powershell
# Enable startup for the current user
uv run magical-girl-glow-down --install-autostart

# Remove the startup entry
uv run magical-girl-glow-down --remove-autostart
```

Startup uses Windows Task Scheduler with this task name:

```text
MagicalGirlGlowDown
```

### Gigabyte Hardware Diagnostics

Close Gigabyte Control Center before running these commands:

```powershell
# Read-only probe
uv run magical-girl-glow-down --gigabyte-probe --debug

# Capture the complete lighting state
uv run magical-girl-glow-down --gigabyte-snapshot --debug

# Black out all supported zones and restore them automatically after 5 seconds
uv run magical-girl-glow-down --gigabyte-test-all --restore-after 5 --debug
```

## Development and Testing

```powershell
uv sync --all-groups
uv run pytest
uv run ruff check .
uv run mypy src
dotnet test helper/MagicalGirlGlowDown.GigabyteHelper.Tests -c Release -v minimal
```

See [Nollie protocol notes](docs/protocol-notes_EN.md) for the protocol analysis
and [Gigabyte validation notes](docs/gigabyte-validation_EN.md) for the hardware
validation process.

## Security and Hardened Runtime

To ensure system and hardware security while running with administrative privileges, this utility implements the following security hardening:

1. **Privilege Model**: The main tray application and the C# helper process both run with elevated administrator privileges.
2. **Packaged Build Boundaries**: Packaged executables strictly ignore any helper or GCC environment overrides (e.g. `MAGICALGIRLGLOWDOWN_GIGABYTE_HELPER` and `MAGICALGIRLGLOWDOWN_GCC_ROOT`), loading only the helper located in their own directory, and searching for GCC only under `%ProgramFiles%\GIGABYTE\Control Center`.
3. **Source Runtime Overrides**: The source execution may honor development overrides for helper or GCC paths, but logs a warning whenever an override path is loaded.
4. **Protected Directories**: The recovery state (`state.json`) and Gigabyte staged DLLs live under `%ProgramData%\MagicalGirlGlowDown`. The app creates and verifies that directory at startup, checks the directory and its parent chain for reparse points, and rejects writable non-administrator ACLs.
5. **Portable Autostart Security**: Enabling boot-on-login for a portable build (outside `Program Files`) prompts the user with a security warning. User confirmation is required before autostart is enabled.
6. **Robust Failure Handling**:
   * **Pending Restore Snapshots**: If GCC is running and recovery fails, the snapshot remains marked `pending_restore` and is preserved. It is retried and marked complete once GCC closes, ensuring no recovery state is lost.
   * **Background Worker Manual Retry**: If the background input-monitoring worker encounters a fatal exception, it shuts down gracefully, shows a "Background service failed" status in the tray, and enables a "Retry background service" action for manual recovery.

## Usage Notes

1. Before first use, back up the current lighting configuration in NollieRGB or
   GCC.
2. Close GCC while debugging Gigabyte control. During normal operation, the app
   detects GCC and yields control automatically.
3. Nollie VID/PID/interface combinations outside the allowlist and unknown
   Gigabyte devices are never written to.
4. If the app is force-closed during blackout, restart it to trigger the
   recovery flow.

## Author

I am **LingMoe404**, an office worker who enjoys experimenting with hardware,
NAS systems, and lighting control.

| Platform | ID / Channel | Link |
| :--- | :--- | :--- |
| Bilibili | **泠萌404** | [Visit](https://space.bilibili.com/136850) |
| YouTube | **泠萌404** | [Visit](https://www.youtube.com/@LingMoe404) |
| Douyin | **泠萌404** | [Visit](https://www.douyin.com/user/MS4wLjABAAAA8fYebaVF2xlczanlTvT-bVoRxLqNjp5Tr01pV8wM88Q) |

## Acknowledgements

This project is built with the following open-source projects, runtimes, and
development tools:

* [Python](https://www.python.org/): Main application and background service
  runtime.
* [PySide6](https://doc.qt.io/qtforpython/): System tray and desktop
  interaction.
* [HIDAPI](https://github.com/libusb/hidapi): Nollie USB HID communication.
* [.NET](https://dotnet.microsoft.com/): Isolated runtime for the Gigabyte
  lighting control component.
* [uv](https://docs.astral.sh/uv/): Python project and dependency management.
* **OpenAI Codex / GPT**: Initial co-development.
* **Google Antigravity / Gemini**: Refactoring, optimization, and agent assistance.

## Behind the Project

MagicalGirlGlowDown is an **AI-assisted project led by LingMoe404**:
* **Initial Development**: Co-developed with OpenAI Codex / GPT.
* **Refactoring & Optimization**: Powered by Google Antigravity / Gemini agents.

Copyright © 2026 LingMoe404
