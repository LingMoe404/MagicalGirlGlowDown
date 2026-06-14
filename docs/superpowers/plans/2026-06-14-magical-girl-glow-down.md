# MagicalGirlGlowDown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a tested Windows tray application that dims every connected Nollie controller after 30 seconds without keyboard, mouse, or controller activity and restores brightness on input.

**Architecture:** A platform-neutral brightness state machine coordinates controller snapshots through a protocol interface. Windows adapters provide idle/input events, process guarding, HID discovery, tray UI, and autostart; deterministic simulation covers all behavior that can be verified without hardware.

**Tech Stack:** Python 3.12.10, uv, PySide6, hidapi, ctypes Windows APIs, pytest, ruff, mypy

---

## File Map

- `pyproject.toml`: package metadata, dependencies, commands, and tool settings.
- `src/magical_girl_glow_down/domain.py`: immutable settings, controller identities, snapshots, and service states.
- `src/magical_girl_glow_down/service.py`: dim/restore state machine and multi-controller orchestration.
- `src/magical_girl_glow_down/storage.py`: atomic settings and recovery-state persistence.
- `src/magical_girl_glow_down/input_monitor.py`: normalized activity sources and idle transition logic.
- `src/magical_girl_glow_down/windows_input.py`: GetLastInputInfo, XInput, WinMM, and Raw Input integration.
- `src/magical_girl_glow_down/protocol.py`: protocol interfaces, HID packet codec, and Nollie driver.
- `src/magical_girl_glow_down/discovery.py`: HID enumeration and supported-device filtering.
- `src/magical_girl_glow_down/app_guard.py`: NollieRGB.exe coexistence guard.
- `src/magical_girl_glow_down/autostart.py`: reversible per-user Windows autostart registration.
- `src/magical_girl_glow_down/simulator.py`: deterministic multi-controller simulation.
- `src/magical_girl_glow_down/tray.py`: PySide6 tray menu and status presentation.
- `src/magical_girl_glow_down/main.py`: dependency composition and CLI.
- `tests/`: unit and integration tests for every behavior above.

### Task 1: Project Skeleton And Domain

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/magical_girl_glow_down/__init__.py`
- Create: `src/magical_girl_glow_down/domain.py`
- Create: `tests/test_domain.py`

- [ ] Write tests proving timeout validation, brightness range validation, and snapshot serialization.
- [ ] Run `uv run pytest tests/test_domain.py -v` and confirm collection fails because the package is absent.
- [ ] Implement the minimal domain models and project metadata.
- [ ] Run the domain tests and `uv run ruff check .`.
- [ ] Commit with `feat: scaffold MagicalGirlGlowDown domain`.

### Task 2: Atomic Recovery Storage

**Files:**
- Create: `src/magical_girl_glow_down/storage.py`
- Create: `tests/test_storage.py`

- [ ] Write tests for defaults, atomic save/load, pending-restore persistence, and corrupt-file quarantine.
- [ ] Run the storage tests and confirm they fail because `StateStore` is absent.
- [ ] Implement JSON persistence using temporary-file replacement.
- [ ] Run the storage and domain tests.
- [ ] Commit with `feat: add recovery state storage`.

### Task 3: Brightness State Machine

**Files:**
- Create: `src/magical_girl_glow_down/service.py`
- Create: `tests/fakes.py`
- Create: `tests/test_service.py`

- [ ] Write tests for all-controller dim/restore, partial read failure, hot-plug, retry, and protection against overwriting a valid snapshot with zero.
- [ ] Run the service tests and confirm they fail because the service is absent.
- [ ] Implement `BrightnessService` against an async controller protocol.
- [ ] Run service, storage, and domain tests.
- [ ] Commit with `feat: orchestrate idle brightness`.

### Task 4: Input Monitoring

**Files:**
- Create: `src/magical_girl_glow_down/input_monitor.py`
- Create: `src/magical_girl_glow_down/windows_input.py`
- Create: `tests/test_input_monitor.py`

- [ ] Write tests for keyboard/mouse idle transitions, controller wake events, dead-zone filtering, and monotonic timestamps.
- [ ] Run the tests and confirm the monitor APIs are missing.
- [ ] Implement the platform-neutral aggregator plus Windows GetLastInputInfo, XInput, WinMM, and generic Raw Input activity sources.
- [ ] Run input tests and static checks.
- [ ] Commit with `feat: monitor Windows user input`.

### Task 5: Nollie HID Protocol And Discovery

**Files:**
- Create: `src/magical_girl_glow_down/protocol.py`
- Create: `src/magical_girl_glow_down/discovery.py`
- Create: `tests/test_protocol.py`
- Create: `docs/protocol-notes.md`

- [ ] Extract packet constants and function behavior from `n_dev_config.pyc` and `n_usb_driver.pyc`, recording evidence in protocol notes.
- [ ] Write packet codec fixtures for general-config reads/writes and HID device normalization.
- [ ] Run protocol tests and confirm they fail because the codec is absent.
- [ ] Implement HID transport, supported-device discovery, current standby-canvas brightness reads, and brightness-only writes.
- [ ] Ensure unsupported firmware fails closed without sending guessed packets.
- [ ] Run protocol tests and static checks.
- [ ] Commit with `feat: add Nollie HID protocol`.

### Task 6: Guard, Autostart, And Tray

**Files:**
- Create: `src/magical_girl_glow_down/app_guard.py`
- Create: `src/magical_girl_glow_down/autostart.py`
- Create: `src/magical_girl_glow_down/tray.py`
- Create: `tests/test_app_guard.py`
- Create: `tests/test_autostart.py`

- [ ] Write tests for detecting NollieRGB.exe and reversible HKCU autostart registration.
- [ ] Run tests and confirm missing APIs.
- [ ] Implement process guarding and registry-backed autostart.
- [ ] Implement tray states and pause, restore, settings, and exit actions.
- [ ] Run focused tests and static checks.
- [ ] Commit with `feat: add tray and Windows integration`.

### Task 7: Composition And Simulator

**Files:**
- Create: `src/magical_girl_glow_down/simulator.py`
- Create: `src/magical_girl_glow_down/main.py`
- Create: `tests/test_simulator.py`
- Create: `tests/test_main.py`
- Modify: `README.md`

- [ ] Write tests for CLI parsing and a multi-controller simulated dim/restore cycle.
- [ ] Run tests and confirm the entry point is absent.
- [ ] Implement `magical-girl-glow-down`, `--simulate`, logging, graceful shutdown, and dependency composition.
- [ ] Document `uv sync`, `uv run magical-girl-glow-down --simulate`, autostart, and hardware validation.
- [ ] Run all tests and the simulator.
- [ ] Commit with `feat: integrate MagicalGirlGlowDown application`.

### Task 8: Final Verification And GitHub Publication

**Files:**
- Create: `.github/workflows/ci.yml`
- Modify: `README.md`

- [ ] Add Windows CI for Python 3.12.10 with `uv sync --all-groups`, pytest, ruff, and mypy.
- [ ] Run `uv sync --all-groups`.
- [ ] Run `uv run pytest -v`, `uv run ruff check .`, and `uv run mypy src`.
- [ ] Run `uv run magical-girl-glow-down --simulate --cycles 1 --idle-seconds 0.1`.
- [ ] Review the complete diff against the design specification.
- [ ] Commit with `ci: validate MagicalGirlGlowDown`.
- [ ] Push `main` baseline and the implementation branch to `LingMoe404/MagicalGirlGlowDown`.
- [ ] Open a draft pull request targeting `main`.
