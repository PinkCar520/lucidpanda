---
name: api-change-guard
description: Guardrail workflow for changing LucidPanda backend APIs. Use when adding, removing, renaming, or refactoring FastAPI endpoints, request/response models, watchlist/calendar/mobile/web routes, or any API consumed by Web, iOS, or tests.
---

# API Change Guard

Use this skill for any backend interface change in `apps/api`.

## Required Checks

1. Read [CLAUDE.md](../../../CLAUDE.md) sections on architecture red lines, cross-end rules, and recent pitfalls.
2. Search for every affected path, schema, and field with `rg`.
3. Check router registration order in `apps/api/src/lucidpanda/api/v1/main.py` and any app bootstrap file.
4. Check whether the change affects Web, iOS, tests, or legacy compatibility routes.
5. Check whether `apps/api/tests/conftest.py` contains hand-written SQLite tables that need matching columns.

## Execution Order

1. Update request/response models first.
2. Update route implementation second.
3. Add compatibility route or compatibility fields if old callers still exist.
4. Update tests and test fixtures.
5. Run targeted tests first, then full `make check`.

## Hard Rules

1. Do not silently remove a route that already exists in Web, iOS, or tests.
2. Do not introduce same-path router conflicts without resolving registration order.
3. Do not update runtime DB usage without syncing SQLite test schema.
4. Do not change response field names like `data`, `success`, `groups`, `sync_time` without updating all callers.
5. Do not leave compatibility behavior undocumented in code. Name it `*_legacy` or `*_compat`.

## Minimum Search Set

Run targeted search before editing:

```bash
rg -n "watchlist|calendar|mobile|web|<field>|<path>" apps/api apps/web mobile/ios
```

## Done Criteria

- API behavior is consistent across read/write paths.
- Tests use the same user/session assumptions as runtime code.
- `make check` passes.
