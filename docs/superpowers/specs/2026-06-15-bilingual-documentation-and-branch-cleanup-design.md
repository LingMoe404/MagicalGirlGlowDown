# Bilingual Documentation and Branch Cleanup Design

## Goal

Make the public documentation usable in both Simplified Chinese and English,
while leaving `main` as the repository's only local and remote branch.

## Documentation Layout

Chinese remains the primary language and keeps the existing filenames:

- `README.md`
- `docs/protocol-notes.md`
- `docs/gigabyte-validation.md`

English translations use an `_EN` suffix:

- `README_EN.md`
- `docs/protocol-notes_EN.md`
- `docs/gigabyte-validation_EN.md`

Every document links to its counterpart near the top. Links inside each README
point to documentation in the same language.

## Translation Rules

- Preserve commands, identifiers, hardware names, registry paths, and protocol
  constants exactly.
- Keep safety limits and hardware support claims equivalent across languages.
- Do not add installer or portable-package claims while those artifacts are not
  distributed.
- Keep Python requirements fixed at 3.12.10.

## Branch Cleanup

The remote currently uses `codex/initial-implementation` as its default branch.
The safe order is:

1. publish all documentation changes to `main`;
2. change the GitHub default branch to `main`;
3. delete `codex/initial-implementation` from the remote;
4. delete the local branch and refresh `origin/HEAD`;
5. verify that only `main` remains.

## Verification

- Check Markdown links and UTF-8 text.
- Run `git diff --check`.
- Run the Python test suite because the documentation describes current CLI
  behavior and supported hardware.
- Confirm GitHub's default branch and remote branch list after cleanup.
