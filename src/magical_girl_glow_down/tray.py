from __future__ import annotations

import asyncio
import logging
import subprocess
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

from .app_guard import is_gcc_running, is_original_app_running
from .autostart import AutostartManager, WindowsTaskScheduler
from .branding import APP_DISPLAY_NAME, APP_NAME, icon_path
from .discovery import discover_controllers
from .domain import AppSettings
from .gigabyte import GigabyteError, GigabyteHelperClient, GigabyteLightingTarget
from .lighting import LightingTarget
from .protocol import NollieController, NollieLightingTarget
from .runtime import runtime_command
from .service import LightingService
from .storage import StateStore
from .windows_input import (
    GameControllerMonitor,
    keyboard_mouse_idle_seconds,
    register_game_controller_raw_input,
)
from .worker import WorkerPolicy

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
        super().__init__(name="MagicalGirlGlowDown-worker", daemon=True)
        self.idle_seconds = idle_seconds
        self.monitor = monitor
        self.bridge = bridge
        self.service = LightingService(StateStore(data_dir))
        self.policy = WorkerPolicy(self.service)
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.restore_event = threading.Event()

    def run(self) -> None:
        asyncio.run(self._run())

    async def _run(self) -> None:
        controllers: list[NollieController] = []
        nollie_targets: list[NollieLightingTarget] = []
        gigabyte_target: GigabyteLightingTarget | None = None
        last_scan = 0.0
        last_dim_scan = 0.0
        next_gigabyte_scan = 0.0
        was_gcc_running = False
        last_app_check = 0.0
        original_running = False
        gcc_is_running = False
        try:
            while not self.stop_event.is_set():
                now = time.monotonic()
                if now - last_app_check >= 2.0:
                    original_running = is_original_app_running()
                    gcc_is_running = is_gcc_running()
                    last_app_check = now
                if not original_running and now - last_scan >= 2:
                    for controller in controllers:
                        controller.close()
                    controllers = discover_controllers()
                    nollie_targets = [
                        NollieLightingTarget(controller) for controller in controllers
                    ]
                    last_scan = now
                if gcc_is_running or was_gcc_running:
                    if gigabyte_target is not None:
                        await gigabyte_target.close()
                    gigabyte_target = None
                    next_gigabyte_scan = now + 2
                elif gigabyte_target is None and now >= next_gigabyte_scan:
                    gigabyte_target = await self._discover_gigabyte_target()
                    next_gigabyte_scan = now + 5
                self.monitor.poll()
                active = (
                    keyboard_mouse_idle_seconds() < self.idle_seconds
                    or now - self.monitor.last_activity < self.idle_seconds
                )
                targets: list[LightingTarget] = list(nollie_targets)
                if gigabyte_target is not None:
                    targets.append(gigabyte_target)
                restore_requested = self.restore_event.is_set()
                should_tick = (
                    active
                    or self.pause_event.is_set()
                    or restore_requested
                    or original_running
                    or gcc_is_running
                    or self.service.state.value != "dimmed"
                    or now - last_dim_scan >= 2
                )
                if should_tick:
                    status = await self.policy.tick(
                        targets,
                        idle=not active,
                        gcc_running=gcc_is_running,
                        nolliergb_running=original_running,
                        manually_paused=self.pause_event.is_set(),
                        restore_requested=restore_requested,
                    )
                    if not active:
                        last_dim_scan = now
                else:
                    status = "Dimmed" if targets else "Waiting for lighting devices"
                self.restore_event.clear()
                if original_running and controllers:
                    for controller in controllers:
                        controller.close()
                    controllers = []
                    nollie_targets = []
                if gcc_is_running:
                    if gigabyte_target is not None:
                        await gigabyte_target.close()
                    gigabyte_target = None
                was_gcc_running = gcc_is_running
                self.bridge.status_changed.emit(status)
                await asyncio.sleep(0.25)
        finally:
            targets = list(nollie_targets)
            if gigabyte_target is not None:
                targets.append(gigabyte_target)
            await self.service.restore(targets)
            if gigabyte_target is not None:
                await gigabyte_target.close()
            for controller in controllers:
                controller.close()

    @staticmethod
    async def _discover_gigabyte_target() -> GigabyteLightingTarget | None:
        client = GigabyteHelperClient()
        try:
            probe = await client.probe()
        except GigabyteError as exc:
            log.debug("Gigabyte lighting probe unavailable: %s", exc)
            return None
        if not probe.zones or any(zone.category == "unsupported" for zone in probe.zones):
            log.warning("Gigabyte lighting has unvalidated zones; backend disabled")
            return None
        return GigabyteLightingTarget(
            client,
            probe.board_fingerprint,
            tuple(zone.id for zone in probe.zones),
        )


def _fallback_icon(color: str) -> QIcon:
    pixmap = QPixmap(32, 32)
    pixmap.fill(QColor("transparent"))
    painter = QPainter(pixmap)
    painter.setBrush(QColor(color))
    painter.setPen(QColor(color))
    painter.drawEllipse(4, 4, 24, 24)
    painter.end()
    return QIcon(pixmap)


def _icon(color: str) -> QIcon:
    icon = QIcon(str(icon_path()))
    return icon if not icon.isNull() else _fallback_icon(color)


def run_tray(idle_seconds: float | None, data_dir: Path) -> int:
    instance = QApplication.instance()
    app = cast(QApplication, instance) if instance else QApplication([])
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setWindowIcon(_icon("#00a9b7"))
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
    host.setWindowTitle(f"{APP_NAME} input host")
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
    command = subprocess.list2cmdline(runtime_command())
    autostart = AutostartManager(WindowsTaskScheduler(), command)
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
    tray.setToolTip(APP_DISPLAY_NAME)

    def update_status(status: str) -> None:
        status_action.setText(status)
        tray.setToolTip(f"{APP_DISPLAY_NAME} - {status}")
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
            APP_DISPLAY_NAME,
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
