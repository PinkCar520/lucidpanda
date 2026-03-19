# Open Source Readiness Report

Date: 2026-03-12

## Summary

The repository is ready for open-source release after completing the hygiene, documentation, and CI adjustments below.

## Required Hygiene

- Remove runtime artifacts from the repo:
  - `.env`
  - `backup_*.sql`
  - `uploads/`
  - `logs/`
  - `ssl-data/`
  - `nginx-logs/`
  - `data/`
- Ensure these are listed in `.gitignore`.
- Rotate any secrets that were present in history.

## Documentation Checklist

- Root `README.md` updated with architecture + quickstart.
- `web/README.md` updated with real frontend instructions.
- Add community health files:
  - `LICENSE`
  - `CONTRIBUTING.md`
  - `CODE_OF_CONDUCT.md`
  - `SECURITY.md`
  - `SUPPORT.md`
  - `CHANGELOG.md`

## CI and Release Gates

- Add CI jobs for `pytest` and `npm test`.
- Restrict auto-deploy:
  - Require manual trigger or environment approval.
  - Avoid running deploy on forks.

## Scope Notes

- Open-source scope: backend + web.
- Mobile client is excluded and should be moved to a private repository.

## Verification

- `git log --all -- .env` returns empty.
- `git log --all -- "backup_*.sql"` returns empty.
- `git grep -n "AUTH_SECRET" $(git rev-list --all)` only matches placeholders in `.env.example`.
