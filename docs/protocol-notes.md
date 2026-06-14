# Nollie HID 协议说明

[English](protocol-notes_EN.md)

静态分析来源：`NollieRGB.exe`，构建时间戳为 2026-05-07，使用 PyInstaller
与 Python 3.11 打包。

归档中包含 `app.core_driver.n_dev_config` 和
`app.core_driver.n_usb_driver`。以下行为通过 `pyi-archive_viewer`、
`pyinstxtractor-ng` 与 `pydisasm` 还原：

- HID 报告格式为 `[0x00 报告 ID] + 负载 + 零填充`，总长度为
  `tx_len + 1`。
- `HID_SET_EFFECT = 250`；`HID_GET_EFFECT = 249`。
- `HID_EFFECT_CH_PARAM = 2`；`HID_EFFECT_CANVAS_LEN = 4`。
- 读取画布数量的负载为 `[249, 4]`；数量位于响应的第 0 字节。
- 读取画布配置的负载为 `[249, 2, canvas]`。
- 配置响应字段位于第 3 至 18 字节；亮度位于第 4 字节。
- 写入配置的负载为 `[250, 2, canvas]`，后接完整的 16 字节配置。
- 默认读取超时为 20 毫秒，最多重试两次，重试间隔为 5 毫秒。
- 未知的 VID、PID 与接口组合不会被打开。

`src/magical_girl_glow_down/discovery.py` 中的设备表只包含从原程序目录
中还原出的当前应用模式设备。Bootloader 与旧设备被明确排除，不会执行
写入。
