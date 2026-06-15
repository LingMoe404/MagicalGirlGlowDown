# 技嘉 RGB 硬件验证

[English](gigabyte-validation_EN.md)

## 只读探测

关闭 GCC 后运行：

```powershell
uv run magical-girl-glow-down --gigabyte-probe --debug
```

此命令会读取：

- Windows BIOS 注册表中的主板身份；
- GCC 程序集文件版本；
- `RGBMotherboard/Profile-0.xml` 中保存的灯光区域数量。

它不会初始化 RGB 控制器，也不会调用任何厂商灯光方法。无法映射的配置
位置会报告为 `unsupported`；在确认其厂商身份前，这些位置保持禁止写入。

## 已验证的主板布局

对于 `X870E AORUS MASTER X3D ICE`，本机 GCC 26.03.25.01 的界面几何布局
与 `rgbcfg.xml` 中的布局 `98` 一致。保存的七个配置位置如下：

| 配置索引 | GCC 区域 | 分类 |
| --- | --- | --- |
| 0 | LED_C | 12V RGB |
| 1 | ARGB_V2_1 | 5V ARGB |
| 2 | ARGB_V2_2 | 5V ARGB |
| 3 | ARGB_V2_3 | 5V ARGB |
| 4 | ARGB_V2_4 | 5V ARGB |
| 5 | IO Shield LED | 板载灯光 |
| 6 | PCH LED | 板载灯光 |

该映射已对照技嘉官方手册中的主板布局和本机 GCC 渲染的坐标进行检查。
它只会用于完全一致的产品名称，其他主板仍保持不支持状态。

## 写入安全

只有满足以下全部条件时，才允许启用硬件写入：

1. 主板指纹与当前计算机匹配；
2. 每个可写区域都具有明确的 `onboard`、`argb5v` 或 `rgb12v` 分类；
3. 快照读取已经过验证；
4. GCC 已关闭；
5. 自动恢复机制已经就绪。

此集成不会调用 BIOS 保存、校准写入或固件更新方法。

临时熄灯流程被有意限制为三个厂商运行时操作：

- `GetLedSetting()` 捕获完整的厂商 JSON 状态；
- `SetAllLedColor(0)` 将所有已验证的主板和接口区域设为黑色；
- 设置 `sInfo = <捕获的 JSON>` 后调用 `Apply(3)`，恢复完全一致的状态。

`SaveSetting`、BIOS 电源状态操作、校准方法和配置写入均不在辅助程序
白名单中。

## 分阶段运行测试

执行以下任一命令前请关闭 GCC。快照操作不会改变灯光：

```powershell
uv run magical-girl-glow-down --gigabyte-snapshot --debug
```

快照和写入命令会请求管理员权限，因为 GCC 的原生主板控制器不会向标准
用户进程报告 MB/LED 身份。只读的 `--gigabyte-probe` 命令仍以非提权方式
运行。

以下命令会熄灭全部七个已验证区域，并在五秒后恢复其灯效、颜色、速度、
亮度和厂商扩展字段：

```powershell
uv run magical-girl-glow-down --gigabyte-test-all --restore-after 5 --debug
```

恢复延迟必须在 1 至 30 秒之间。恢复逻辑位于 `finally` 块中，取消流程也会
执行恢复。当 `GCC.exe` 正在运行时，辅助程序会拒绝快照、熄灯和恢复操作。

## 加固安全边界与恢复策略

为了确保管理员权限下主板灯效控制的安全性与恢复可靠性，系统设计了以下机制：

1. **打包运行隔离**：在打包发布版本中，任何 helper 或 GCC 的环境变量路径覆盖（`MAGICALGIRLGLOWDOWN_GIGABYTE_HELPER` 和 `MAGICALGIRLGLOWDOWN_GCC_ROOT`）都将被严格忽略。程序仅在固定路径 `%ProgramFiles%\GIGABYTE\Control Center` 下寻找 GCC 依赖组件，防止通过注入环境变量加载不安全的代码。
2. **保护暂存与存储目录**：C# 辅助程序的 DLL 暂存区与 Python 持久化恢复状态均保存在全局 `%ProgramData%\MagicalGirlGlowDown` 目录下。该目录由特权程序在创建时配置 ACL（仅允许内置 Administrators 组和 SYSTEM 拥有写权限，普通用户只读/拒绝写）。在加载或写入前，系统会强校验该目录及其祖先目录是否为重解析点（符号链接/连接点），若检测到重解析点则直接拒绝执行，彻底规避 staging DLL 篡改或任意文件写入漏洞。
3. **GCC 冲突与待机快照保护**：在熄灯待机期间若 GCC 启动，本工具会优雅释放主板写入权限。若因此导致在 handoff 前恢复失败，快照会置为 `pending_restore` 并安全保留在 `%ProgramData%\MagicalGirlGlowDown\state.json` 中。待 GCC 关闭后，本工具会重新探测并优先应用并完成此 pending 恢复，确保硬件效果不遗失。
