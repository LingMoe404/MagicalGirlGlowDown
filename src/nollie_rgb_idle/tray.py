from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
import threading
import time
from ctypes import wintypes
from pathlib import Path
from typing import cast

from PySide6.QtCore import QAbstractNativeEventFilter, QByteArray, QObject, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QInputDialog,
    QMenu,
    QSystemTrayIcon,
    QWidget,
)

from .app_guard import original_app_running
from .autostart import AutostartManager, WindowsRunRegistry
from .discovery import discover_controllers
from .domain import AppSettings
from .protocol import NollieController
from .service import BrightnessService
from .storage import StateStore
from .windows_input import (
    GameControllerMonitor,
    keyboard_mouse_idle_seconds,
    register_game_controller_raw_input,
)

log = logging.getLogger(__name__)
WM_INPUT = 0x00FF


class StatusBridge(QObject):
    status_changed = Signal(str)


class RawInputFilter(QAbstractNativeEventFilter):
    def __init__(self, monitor: GameControllerMonitor) -> None:
        super().__init__()
        self.monitor = monitor

    def nativeEventFilter(
        self,
        _event_type: QByteArray | bytes | bytearray | memoryview[int],
        message: int,
    ) -> tuple[bool, int]:
        msg = wintypes.MSG.from_address(int(message))
        if msg.message == WM_INPUT:
            self.monitor.record_raw_input()
        return False, 0


class Worker(threading.Thread):
    def __init__(
        self,
        idle_seconds: float,
        data_dir: Path,
        monitor: GameControllerMonitor,
        bridge: StatusBridge,
    ) -> None:
        super().__init__(name="NollieRGBIdle-worker", daemon=True)
        self.idle_seconds = idle_seconds
        self.monitor = monitor
        self.bridge = bridge
        self.service = BrightnessService(StateStore(data_dir))
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.restore_event = threading.Event()

    def run(self) -> None:
        asyncio.run(self._run())

    async def _run(self) -> None:
        controllers: list[NollieController] = []
        last_scan = 0.0
        last_dim_scan = 0.0
        try:
            while not self.stop_event.is_set():
                now = time.monotonic()
                original_running = original_app_running()
                if not original_running and now - last_scan >= 2:
                    for controller in controllers:
                        controller.close()
                    controllers = discover_controllers()
                    last_scan = now
                self.monitor.poll()
                paused = self.pause_event.is_set() or original_running
                active = (
                    keyboard_mouse_idle_seconds() < self.idle_seconds
                    or now - self.monitor.last_activity < self.idle_seconds
                )
                if paused or active or self.restore_event.is_set():
                    if self.service.has_pending_restore:
                        await self.service.restore(controllers)
                    self.restore_event.clear()
                    status = "Paused: NollieRGB is open" if original_running else "Active"
                    if original_running and controllers:
                        for controller in controllers:
                            controller.close()
                        controllers = []
                else:
                    if self.service.state.value != "dimmed" or now - last_dim_scan >= 2:
                        await self.service.dim(controllers)
                        last_dim_scan = now
                    status = "Dimmed" if controllers else "Waiting for controller"
                self.bridge.status_changed.emit(status)
                await asyncio.sleep(0.25)
        finally:
            await self.service.restore(controllers)
            for controller in controllers:
                controller.close()


def _icon(color: str) -> QIcon:
    pixmap = QPixmap(32, 32)
    pixmap.fill(QColor("transparent"))
    painter = QPainter(pixmap)
    painter.setBrush(QColor(color))
    painter.setPen(QColor(color))
    painter.drawEllipse(4, 4, 24, 24)
    painter.end()
    return QIcon(pixmap)


def run_tray(idle_seconds: float | None, data_dir: Path) -> int:
    instance = QApplication.instance()
    app = cast(QApplication, instance) if instance else QApplication([])
    app.setQuitOnLastWindowClosed(False)
    store = StateStore(data_dir)
    settings = store.load_settings()
    if idle_seconds is not None:
        settings = AppSettings(
            idle_seconds=idle_seconds,
            axis_dead_zone=settings.axis_dead_zone,
            axis_change_threshold=settings.axis_change_threshold,
            enabled=settings.enabled,
            autostart=settings.autostart,
        )
        store.save_settings(settings)
    monitor = GameControllerMonitor()
    bridge = StatusBridge()
    worker = Worker(settings.idle_seconds, data_dir, monitor, bridge)

    host = QWidget()
    host.setWindowTitle("NollieRGBIdle input host")
    host.resize(1, 1)
    host.show()
    host.hide()
    register_game_controller_raw_input(int(host.winId()))
    native_filter = RawInputFilter(monitor)
    app.installNativeEventFilter(native_filter)

    tray = QSystemTrayIcon(_icon("#00a9b7"), app)
    menu = QMenu()
    status_action = QAction("Starting...", menu)
    status_action.setEnabled(False)
    pause_action = QAction("Pause", menu)
    restore_action = QAction("Restore lighting now", menu)
    settings_action = QAction("Set idle timeout...", menu)
    autostart_action = QAction("Start with Windows", menu)
    autostart_action.setCheckable(True)
    exit_action = QAction("Exit", menu)
    command = subprocess.list2cmdline([sys.executable, "-m", "nollie_rgb_idle.main"])
    autostart = AutostartManager(WindowsRunRegistry(), command)
    autostart_action.setChecked(autostart.enabled())
    menu.addAction(status_action)
    menu.addSeparator()
    menu.addAction(pause_action)
    menu.addAction(restore_action)
    menu.addAction(settings_action)
    menu.addAction(autostart_action)
    menu.addSeparator()
    menu.addAction(exit_action)
    tray.setContextMenu(menu)
    tray.setToolTip("NollieRGBIdle")

    def update_status(status: str) -> None:
        status_action.setText(status)
        tray.setToolTip(f"NollieRGBIdle - {status}")
        tray.setIcon(_icon("#777777" if status.startswith("Paused") else "#00a9b7"))

    def toggle_pause() -> None:
        if worker.pause_event.is_set():
            worker.pause_event.clear()
            pause_action.setText("Pause")
        else:
            worker.pause_event.set()
            worker.restore_event.set()
            pause_action.setText("Resume")

    def shutdown() -> None:
        worker.stop_event.set()
        tray.hide()
        QTimer.singleShot(500, app.quit)

    def change_timeout() -> None:
        value, accepted = QInputDialog.getDouble(
            None,
            "NollieRGBIdle",
            "Idle timeout (seconds):",
            worker.idle_seconds,
            1,
            86400,
            1,
        )
        if not accepted:
            return
        worker.idle_seconds = value
        current = store.load_settings()
        store.save_settings(
            AppSettings(
                idle_seconds=value,
                axis_dead_zone=current.axis_dead_zone,
                axis_change_threshold=current.axis_change_threshold,
                enabled=current.enabled,
                autostart=autostart_action.isChecked(),
            )
        )

    def toggle_autostart(checked: bool) -> None:
        if checked:
            autostart.enable()
        else:
            autostart.disable()
        current = store.load_settings()
        store.save_settings(
            AppSettings(
                idle_seconds=current.idle_seconds,
                axis_dead_zone=current.axis_dead_zone,
                axis_change_threshold=current.axis_change_threshold,
                enabled=current.enabled,
                autostart=checked,
            )
        )

    bridge.status_changed.connect(update_status)
    pause_action.triggered.connect(toggle_pause)
    restore_action.triggered.connect(worker.restore_event.set)
    settings_action.triggered.connect(change_timeout)
    autostart_action.toggled.connect(toggle_autostart)
    exit_action.triggered.connect(shutdown)
    tray.show()
    worker.start()
    result = app.exec()
    worker.stop_event.set()
    worker.join(timeout=3)
    return result
