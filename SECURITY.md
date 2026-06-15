# 安全策略 (Security Policy)

[← 返回主页 (Back to README)](README.md)

我们非常重视 **魔法少女·静谧霓虹 (Magical Girl Glow Down)** 的安全性。由于本工具在运行过程中涉及 Windows 系统最高权限（管理员权限）以及硬件底层控制，我们将安全防范置于极高优先级。

## 支持的版本 (Supported Versions)

目前我们仅对最新发布的版本提供安全更新支持。

| 版本 | 支持状态 |
| :--- | :--- |
| v0.1.x | :white_check_mark: |
| < 0.1 | :x: |

## 权限与安全边界声明 (Privileges & Security Boundary)

为了帮助安全研究员与用户了解安全设计，本工具的权限边界规定如下：

1.  **管理员权限 (UAC)**: 
    *   **原因**: 技嘉主板的 RGB 写入需要加载底层的底层硬件驱动 DLL，该操作只能由管理员权限的进程发起。
    *   **防范**: 我们编写了独立的 **C# 辅助进程 (`MagicalGirlGlowDown.GigabyteHelper.exe`)** 来隔离硬件操作。主 Python 托盘程序仅在启动时一次性请求 UAC 提权。
2.  **开机启动安全性 (Task Scheduler)**:
    *   开机启动通过 Windows 任务计划程序实现，以避开每次登录都弹出 UAC 提权提示。
    *   注册任务被严格限制为仅执行本软件目录内的可执行文件，防止恶意软件篡改路径进行提权攻击。
3.  **硬件写入安全 (Write Protection)**:
    *   为了防止因地址冲突导致硬件损坏，程序对主板硬件端口和配置参数进行了严格的**只读白名单过滤**。任何未经验证的设备/寄存器写入都会触发拒绝写入，并输出 `unsupported` 日志。

## 报告漏洞 (Reporting a Vulnerability)

如果您在本软件或辅助客户端中发现了任何安全漏洞（例如提权漏洞、缓冲区溢出或逻辑安全缺陷），请**不要**在 GitHub Issues 中公开提交。

请通过以下私密渠道联系维护者：

1.  **发送邮件**: 将漏洞详情发送至 `lw4289@gmail.com`。
2.  **私信联系**: 通过 Bilibili 私信联系 **泠萌404** `UID:136850`。

我们会在收到报告后的 **48 小时内** 给予答复，并尽快评估、修复与发布安全更新。

---

# Security Policy (English)

← Back to README

We take the security of **Magical Girl: Tranquil Neon (Magical Girl Glow Down)** very seriously. Since this utility operates with elevated Windows privileges (Administrator) and interacts directly with hardware registers, security is our top priority.

## Supported Versions

We currently only support security updates for the latest released version.

| Version | Supported |
| :--- | :--- |
| v0.1.x | :white_check_mark: |
| < 0.1 | :x: |

## Privilege & Security Boundary Declaration

To help security researchers and users understand our architecture:

1.  **Administrator Privileges (UAC)**:
    *   **Why**: Interfacing with Gigabyte motherboard RGB SDKs requires low-level kernel driver communication, which can only be initiated by processes with elevated privileges.
    *   **Mitigation**: We isolated hardware writes to a standalone **C# helper process (`MagicalGirlGlowDown.GigabyteHelper.exe`)**. The main Python tray application requests UAC elevation once during startup.
2.  **Startup Task Security (Task Scheduler)**:
    *   The boot-on-login feature registers a Windows Task Scheduler entry to bypass UAC prompts.
    *   This task is strictly hardcoded to launch the specific executable path in the program folder, preventing path traversal or privilege hijacking.
3.  **Hardware Write Safety**:
    *   To prevent hardware damage from incorrect register writes, we enforce a strict **read-only whitelist** for motherboard IDs and lighting zones. Any unsupported configuration defaults to write-protected.

## Reporting a Vulnerability

If you discover a security vulnerability (such as privilege escalation, buffer overflow, or logic flaws), please **do not** open a public GitHub Issue.

Please report it privately to the maintainer via:

1.  **Email**: Send vulnerability details to `lw4289@gmail.com`.
2.  **Direct Message**: Message **LingMoe404** `UID:136850` on Bilibili.

We will acknowledge receipt within **48 hours** and work on a fix as quickly as possible.
