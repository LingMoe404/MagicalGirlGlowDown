# Bilingual Documentation and Branch Cleanup Plan

**Goal:** Publish complete Chinese and English documentation, then leave
`main` as the only repository branch.

## Task 1: Add Language Navigation

1. Add an English-language link near the top of `README.md`.
2. Create `README_EN.md` as a complete translation.
3. Keep commands, support claims, and safety notes synchronized.

## Task 2: Translate Technical Notes

1. Rewrite `docs/protocol-notes.md` as the Chinese primary document.
2. Create `docs/protocol-notes_EN.md` from the existing English content.
3. Rewrite `docs/gigabyte-validation.md` as the Chinese primary document.
4. Create `docs/gigabyte-validation_EN.md` from the existing English content.
5. Add reciprocal language links to all four technical documents.

## Task 3: Validate and Publish Documentation

1. Check all local Markdown links.
2. Run `git diff --check`.
3. Run `uv run pytest -q`.
4. Commit and push the documentation to `main`.

## Task 4: Make `main` the Only Branch

1. Change the GitHub default branch to `main`.
2. Delete remote `codex/initial-implementation`.
3. Delete local `codex/initial-implementation`.
4. Refresh `origin/HEAD`.
5. Verify local branches, remote branches, and the remote default branch.
