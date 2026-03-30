---
name: frontend-api-integration
description: Workflow for connecting LucidPanda Web frontend to backend APIs. Use when adding or changing hooks, lib API clients, page data flows, response types, loading states, or when preventing components from guessing backend contracts.
---

# Frontend API Integration

Use this skill when changing `apps/web` code that depends on backend APIs.

## Required Checks

1. Read the backend response model or route implementation first.
2. Search for existing hook and API client usage with `rg`.
3. Identify the stable contract: endpoint, params, response fields, loading states, error states.

## Execution Order

1. Update `lib/` request layer first.
2. Update TypeScript types second.
3. Update `hooks/api/` third.
4. Update page/component consumers last.

## Hard Rules

1. Do not fetch directly in a component if a hook should own the data flow.
2. Do not hardcode fallback URLs as a permanent solution.
3. Do not spread backend response parsing across multiple components.
4. Do not use `any` when the backend contract is knowable.
5. Do not add UI for happy path only. Include loading, empty, and error states.

## Search Pattern

```bash
rg -n "<endpoint>|<field>|useQuery|hooks/api|lib/" apps/web
```

## Mapping Rule

If display names differ from backend field names, convert them in one place:

- hook mapper
- API client mapper

Never scatter field translation across components.

## Done Criteria

- API type is explicit.
- Hook owns the fetch and cache behavior.
- Component only consumes typed props/data.
- Loading, empty, and error states are all handled.
