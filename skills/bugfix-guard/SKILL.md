---
name: bugfix-guard
description: Root-cause-first workflow for fixing bugs in LucidPanda. Use when tests fail, make check breaks, an endpoint behaves inconsistently, or an AI agent must avoid trial-and-error edits in fragile backend or frontend code.
---

# Bugfix Guard

Use this skill for bug fixing, not feature work.

## Workflow

1. Reproduce the bug with the narrowest command possible.
2. Read the failing code path completely before editing.
3. Identify whether the issue is runtime logic, test fixture drift, schema drift, route conflict, or compatibility break.
4. Fix the root cause first.
5. Only after the root cause is fixed, adjust tests or fixtures that were out of sync.
6. Re-run the narrow test, then broader checks.

## Root Cause Checklist

1. Is the wrong route being hit because of registration order?
2. Is the test using a different user/session than the API code?
3. Is SQLite test schema missing runtime columns?
4. Is a legacy path still being called by tests or clients?
5. Is the code writing data in one shape and reading another?

## Hard Rules

1. Do not weaken assertions just to get green tests.
2. Do not patch multiple unrelated theories in one pass.
3. Do not change large files opportunistically during a bugfix.
4. Do not assume runtime and test DB schemas match. Verify.

## Good Output

A bugfix should end with:

- concrete root cause
- minimal code change
- updated fixture/schema only if necessary
- passing targeted verification

## High-Risk Files

Read full context before editing:

- `apps/api/src/lucidpanda/api/v1/routers/web.py`
- `apps/api/src/lucidpanda/api/v1/routers/watchlist_v2.py`
- `apps/api/src/lucidpanda/core/fund_engine.py`
- `apps/web/components/BacktestStats.tsx`
