# Changelog

All notable software-engineering changes to AI-Kill-Cancer are recorded here.

## [1.0.3] - 2026-08-10

### Added
- Local-first SQLite workspace mode with integrity checks, backup/restore, restart persistence, and pre-upgrade automatic backup.
- Controlled local CSV import flow: validate → preview → explicit import.
- Duplicate-aware import preview and persistent `import-history.jsonl` audit trail.
- Local Workspace Import UI with local/research SQLite write guard.
- Synthetic PTC demo dataset, deterministic UUIDv5 bootstrap, schema/row/domain/JSON-list validation.
- Synthetic deep-link hydration for Recommendation, Clinical Decision, Treatment Plan, Knowledge Graph, PTC Research, PTC Integrated Workbench, and PTC Command Center.
- Navbar preservation of `demo_case` / `data_mode=synthetic` across demo routes.
- Production multi-route Chromium gate and API JSON smoke coverage.
- Traceability persistence E2E across a real SQLite close/re-init cycle.

### Fixed
- Vercel DB cold-start failures caused by unsafe default database selection.
- Demo CSV quoting, fusion-row alignment, evidence foreign-key keys, and JSON-list payload defects that caused API 500/503 responses.
- `/api/v1/ptc-data-quality/overview` and related DB-backed production API initialization failures.

### Safety / Scope
- Synthetic demo data remains research/demo-only and is not clinical evidence.
- Version maturity describes software engineering status only; it does not imply clinical validation, efficacy, diagnosis, or treatment approval.

## [1.0.2]
- Previous repository release baseline before the Local-First Research & Demo Showcase hardening cycle.
