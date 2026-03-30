---
name: merge-guard
description: Safe merge workflow for LucidPanda. Use before commit, merge, or push when you need to verify change scope, remove generated files, avoid unrelated docs deletions, and confirm the branch is safe to merge into main.
---

# Merge Guard

Use this skill before merging any branch into `main`.

## Required Checks

1. Review `git status --short`.
2. Review `git diff --stat` or `git show --stat`.
3. Check for generated files, especially coverage, logs, caches, and snapshots.
4. Check for unrelated `docs/`, image, or asset deletions.
5. Check commit messages for low-signal names like `fix`, `update`, `tmp`.

## Hard Rules

1. Do not merge generated files such as `coverage.xml`.
2. Do not merge broad unrelated deletions with functional fixes.
3. Do not merge if the branch contains scope-mixed changes that should be split.
4. Do not merge without running the relevant verification command for the touched area.

## Pre-Merge Commands

```bash
git status --short --branch
git diff --stat main...HEAD
git log --oneline --decorate main..HEAD
```

## Review Heuristics

1. Functional fix + mass docs deletion in one branch is a red flag.
2. Test updates without corresponding runtime fix are a red flag.
3. Coverage artifacts or one-off generated files should be removed before merge.
4. If merge output surprises you, stop and split the branch instead of pushing through.

## Done Criteria

- Diff scope matches the user task.
- No generated artifacts are included.
- No unrelated docs or assets are deleted.
- Verification already passed on the merge candidate.
