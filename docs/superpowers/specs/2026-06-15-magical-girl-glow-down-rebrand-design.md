# MagicalGirlGlowDown Rebrand Design

## Goal

Rename the complete application from its temporary Nollie-specific project
identity to `MagicalGirlGlowDown`, while preserving Nollie and Gigabyte hardware
behavior.

## Naming

| Surface | Value |
| --- | --- |
| Product, repository, executable, data directory | `MagicalGirlGlowDown` |
| Chinese display name | `魔法少女·静谧霓虹` |
| Python distribution and CLI | `magical-girl-glow-down` |
| Python import package | `magical_girl_glow_down` |
| Windows AppUserModelID | `LingMoe404.MagicalGirlGlowDown` |
| .NET helper | `MagicalGirlGlowDown.GigabyteHelper` |
| Supported Python | exactly `3.12.10` for development and CI |

`NollieRGB.exe`, Nollie controller model names, and Gigabyte Control Center
remain unchanged because they identify external products and hardware.

## Application Identity

Brand constants live in one Python module and are consumed by the CLI, tray,
autostart integration, application-data path, and Windows AppUserModelID setup.
The version remains sourced from `pyproject.toml` instead of being duplicated in
application code.

The supplied `logo.ico` is packaged with the Python module and used by the
system tray. A generated fallback icon remains available if the asset cannot be
loaded.

## Verification

The rename is accepted when:

1. Python imports only use `magical_girl_glow_down`.
2. The CLI starts as `uv run magical-girl-glow-down`.
3. Python 3.12.10 runs all Python tests, Ruff, Mypy, and simulation.
4. The renamed .NET helper builds and passes all tests.
5. Runtime source and active documentation contain no obsolete internal package,
   CLI, namespace, helper, data-directory, or autostart names.
6. The repository lives at `A:\Code\MagicalGirlGlowDown` and pushes to
   `LingMoe404/MagicalGirlGlowDown`.
