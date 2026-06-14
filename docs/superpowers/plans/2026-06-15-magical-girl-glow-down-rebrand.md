# MagicalGirlGlowDown Rebrand Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Fully rename and relocate the working application, pin Python 3.12.10,
package the supplied logo, preserve existing user state, and publish the result.

**Architecture:** Keep the existing `src` layout and hardware services. Add a
small branding module as the single identity source, mechanically rename Python
and .NET namespaces, and isolate compatibility strings in migration code.

**Tech Stack:** Python 3.12.10, uv, PySide6, HIDAPI, .NET 10, pytest, Ruff, Mypy,
xUnit, GitHub Actions.

---

### Task 1: Rename Python Packaging

**Files:**
- Rename: the legacy Python package directory to `src/magical_girl_glow_down`
- Modify: `pyproject.toml`
- Modify: `.python-version`
- Modify: `.github/workflows/ci.yml`
- Modify: all Python tests

- [x] Rename the import package and replace test imports.
- [x] Set the distribution and CLI to `magical-girl-glow-down`.
- [x] Require Python `>=3.12.10,<3.13` and set Ruff/Mypy to Python 3.12.
- [x] Regenerate `uv.lock`.
- [x] Run `uv run pytest -q` and require all tests to pass.

### Task 2: Centralize Runtime Branding and Migration

**Files:**
- Create: `src/magical_girl_glow_down/branding.py`
- Modify: `src/magical_girl_glow_down/main.py`
- Modify: `src/magical_girl_glow_down/tray.py`
- Modify: `src/magical_girl_glow_down/autostart.py`
- Modify: `src/magical_girl_glow_down/privilege.py`
- Test: `tests/test_branding.py`
- Test: `tests/test_main.py`
- Test: `tests/test_autostart.py`

- [x] Add failing tests for stable brand constants, data-directory migration,
  CLI identity, and legacy autostart cleanup.
- [x] Run the focused tests and confirm they fail because the new API is absent.
- [x] Implement the branding module and migration behavior.
- [x] Set `LingMoe404.MagicalGirlGlowDown` before creating the Qt application.
- [x] Run focused tests and then the complete Python suite.

### Task 3: Package and Use the Logo

**Files:**
- Move: `logo.ico` to `src/magical_girl_glow_down/assets/logo.ico`
- Modify: `src/magical_girl_glow_down/branding.py`
- Modify: `src/magical_girl_glow_down/tray.py`
- Test: `tests/test_branding.py`

- [x] Add a failing assertion that the packaged icon path exists.
- [x] Move the supplied ICO into package data.
- [x] Load it for the tray and retain the generated icon as a fallback.
- [x] Run the branding and tray worker tests.

### Task 4: Rename the Gigabyte Helper

**Files:**
- Rename: `helper/MagicalGirlGlowDown.GigabyteHelper`
- Rename: `helper/MagicalGirlGlowDown.GigabyteHelper.Tests`
- Modify: C# namespaces, project references, helper discovery, and build script

- [x] Rename both .NET projects to `MagicalGirlGlowDown.GigabyteHelper`.
- [x] Replace namespaces and the helper process identity.
- [x] Rename helper environment variables to the new product prefix.
- [x] Build the packaged helper.
- [x] Run `dotnet test helper/MagicalGirlGlowDown.GigabyteHelper.Tests -c Release -v minimal`.

### Task 5: Update Documentation and Repository Identity

**Files:**
- Modify: `README.md`
- Modify: `docs/protocol-notes.md`
- Modify: `docs/gigabyte-validation.md`
- Modify: existing design and plan documents
- Modify: Git remote `origin`

- [x] Change all active commands and source paths to the new names.
- [x] Keep external `NollieRGB.exe` references intact.
- [x] Set `origin` to `https://github.com/LingMoe404/MagicalGirlGlowDown.git`.
- [x] Search the working tree for obsolete internal identifiers and allow only
  documented migration constants.

### Task 6: Final Verification and Publication

**Files:**
- Verify all changed files

- [x] Run `uv run pytest -q`.
- [x] Run `uv run ruff check .`.
- [x] Run `uv run mypy src`.
- [x] Run `uv run magical-girl-glow-down --simulate --cycles 1 --idle-seconds 0.1`.
- [x] Run the complete .NET test project.
- [x] Run `git diff --check`.
- [x] Commit the complete rename and push `main`.
