from __future__ import annotations

import asyncio
import logging
import subprocess
import threading
import time
from ctypes import wintypes
from pathlib import Path
from collections.abc import Callable
from typing import cast

from PySide6.QtCore import QAbstractNativeEventFilter, QByteArray, QObject, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QInputDialog,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
    QWidget,
)

from .app_guard import is_gcc_running, is_original_app_running
from .autostart import AutostartManager, WindowsTaskScheduler, requires_portable_confirmation
from .branding import APP_DISPLAY_NAME, APP_NAME, icon_path
from .discovery import discover_controllers
from .domain import AppSettings
from .gigabyte import GigabyteError, GigabyteHelperClient, GigabyteLightingTarget
from .i18n import t
from .lighting import LightingTarget
from .protocol import NollieController, NollieLightingTarget
from .runtime import runtime_command
from .service import LightingService
from .storage import StateStore
from .windows_input import (
    GameControllerMonitor,
    keyboard_mouse_idle_seconds,
    register_game_controller_raw_input,
    read_raw_input_report,
)
from .worker import WorkerPolicy

log = logging.getLogger(__name__)
WM_INPUT = 0x00FF


class StatusBridge(QObject):
    status_changed = Signal(str)
    worker_failed = Signal(str)


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
            raw = read_raw_input_report(int(msg.lParam))
            if raw is not None:
                device, report = raw
                self.monitor.record_raw_report(device, report)
        return False, 0


class Worker(threading.Thread):
    def __init__(
        self,
        idle_seconds: float,
        data_dir: Path,
        monitor: GameControllerMonitor,
        bridge: StatusBridge,
        state_dir: Path | None = None,
    ) -> None:
        super().__init__(name="MagicalGirlGlowDown-worker", daemon=True)
        self.idle_seconds = idle_seconds
        self.monitor = monitor
        self.bridge = bridge
        self.service = LightingService(StateStore(data_dir, state_dir))
        self.policy = WorkerPolicy(self.service)
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.restore_event = threading.Event()

    def run(self) -> None:
        try:
            asyncio.run(self._run())
        except Exception as exc:
            log.exception("Lighting worker terminated")
            self.bridge.worker_failed.emit(str(exc))

    async def _transition_gigabyte_target(
        self,
        target: GigabyteLightingTarget | None,
        *,
        gcc_running: bool,
        was_gcc_running: bool,
        now: float,
        next_scan: float,
    ) -> tuple[GigabyteLightingTarget | None, float]:
        if gcc_running:
            if target is not None:
                await self.service.restore([target])
                await target.close()
            return None, now + 2

        if target is None and now >= next_scan:
            target = await self._discover_gigabyte_target()
            next_scan = now + 5

        if was_gcc_running and target is not None:
            await self.service.restore([target])

        return target, next_scan

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
                gigabyte_target, next_gigabyte_scan = await self._transition_gigabyte_target(
                    gigabyte_target,
                    gcc_running=gcc_is_running,
                    was_gcc_running=was_gcc_running,
                    now=now,
                    next_scan=next_gigabyte_scan,
                )
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


class WorkerController:
    def __init__(self, factory: Callable[[], Worker]) -> None:
        self._factory = factory
        self.worker: Worker | None = None

    def start(self) -> Worker:
        if self.worker is not None and self.worker.is_alive():
            raise RuntimeError("lighting worker is already running")
        self.worker = self._factory()
        self.worker.start()
        return self.worker

    def restart(self) -> Worker:
        if self.worker is not None and self.worker.is_alive():
            raise RuntimeError("lighting worker is already running")
        return self.start()

    def stop(self) -> None:
        if self.worker is not None:
            self.worker.stop_event.set()


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


def run_tray(
    idle_seconds: float | None,
    settings_dir: Path,
    state_dir: Path | None = None,
) -> int:
    instance = QApplication.instance()
    app = cast(QApplication, instance) if instance else QApplication([])
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setWindowIcon(_icon("#00a9b7"))
    store = StateStore(settings_dir, state_dir)
    store.migrate_legacy_state()
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

    def worker_factory() -> Worker:
        return Worker(
            settings.idle_seconds,
            settings_dir,
            monitor,
            bridge,
            state_dir=state_dir,
        )

    worker_controller = WorkerController(worker_factory)

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
    status_action = QAction(t("starting"), menu)
    status_action.setEnabled(False)
    retry_action = QAction(t("retry_worker"), menu)
    retry_action.setEnabled(False)
    pause_action = QAction(t("pause"), menu)
    restore_action = QAction(t("restore_now"), menu)
    settings_action = QAction(t("set_timeout"), menu)
    autostart_action = QAction(t("start_with_windows"), menu)
    autostart_action.setCheckable(True)
    exit_action = QAction(t("exit"), menu)
    command = subprocess.list2cmdline(runtime_command())
    autostart = AutostartManager(WindowsTaskScheduler(), command)
    autostart_action.setChecked(autostart.enabled())
    menu.addAction(status_action)
    menu.addAction(retry_action)
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
        local_status = status
        if status == "Paused":
            local_status = t("paused")
        elif status == "Active":
            local_status = t("running")
        elif status == "Dimmed":
            local_status = t("idle")
        elif status == "Waiting for lighting devices":
            local_status = t("waiting_devices")
        elif status == "Paused: GCC and NollieRGB are open":
            local_status = t("paused_both_open")
        elif status == "Gigabyte paused: GCC is open":
            local_status = t("paused_gcc_open")
        elif status == "Nollie paused: NollieRGB is open":
            local_status = t("paused_nolliergb_open")

        status_action.setText(local_status)
        tray.setToolTip(f"{APP_DISPLAY_NAME} - {local_status}")
        tray.setIcon(_icon("#777777" if status.startswith("Paused") else "#00a9b7"))

    def toggle_pause() -> None:
        w = worker_controller.worker
        if w is None:
            return
        if w.pause_event.is_set():
            w.pause_event.clear()
            pause_action.setText(t("pause"))
        else:
            w.pause_event.set()
            w.restore_event.set()
            pause_action.setText(t("resume"))

    def restore_now() -> None:
        w = worker_controller.worker
        if w is not None:
            w.restore_event.set()

    def shutdown() -> None:
        worker_controller.stop()
        tray.hide()
        QTimer.singleShot(500, app.quit)

    def change_timeout() -> None:
        nonlocal settings
        w = worker_controller.worker
        current_idle = w.idle_seconds if w is not None else settings.idle_seconds
        value, accepted = QInputDialog.getDouble(
            None,
            t("timeout_dialog_title"),
            t("timeout_dialog_label"),
            current_idle,
            1,
            86400,
            1,
        )
        if not accepted:
            return
        if w is not None:
            w.idle_seconds = value
        settings = AppSettings(
            idle_seconds=value,
            axis_dead_zone=settings.axis_dead_zone,
            axis_change_threshold=settings.axis_change_threshold,
            enabled=settings.enabled,
            autostart=settings.autostart,
        )
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
        if checked and requires_portable_confirmation(Path(runtime_command()[0])):
            answer = QMessageBox.warning(
                None,
                t("portable_autostart_warning_title"),
                t("portable_autostart_warning_message"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                autostart_action.blockSignals(True)
                autostart_action.setChecked(False)
                autostart_action.blockSignals(False)
                return
        try:
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
        except Exception as e:
            autostart_action.blockSignals(True)
            autostart_action.setChecked(not checked)
            autostart_action.blockSignals(False)

            QMessageBox.critical(
                None,
                t("autostart_failed_title"),
                t("autostart_failed_msg", error=str(e)),
            )

    def handle_worker_failure(message: str) -> None:
        log.error("Background service failed: %s", message)
        status_action.setText(t("worker_failed"))
        tray.setToolTip(f"{APP_DISPLAY_NAME} - {t('worker_failed')}")
        retry_action.setEnabled(True)

    def retry_worker() -> None:
        retry_action.setEnabled(False)
        status_action.setText(t("starting"))
        try:
            worker_controller.restart()
        except RuntimeError as exc:
            log.warning("Could not restart worker: %s", exc)
            retry_action.setEnabled(True)

    bridge.status_changed.connect(update_status)
    bridge.worker_failed.connect(handle_worker_failure)
    pause_action.triggered.connect(toggle_pause)
    restore_action.triggered.connect(restore_now)
    settings_action.triggered.connect(change_timeout)
    autostart_action.toggled.connect(toggle_autostart)
    retry_action.triggered.connect(retry_worker)
    exit_action.triggered.connect(shutdown)
    tray.show()
    worker_controller.start()
    result = app.exec()
    worker_controller.stop()
    if worker_controller.worker is not None:
        worker_controller.worker.join(timeout=3)
    return result
