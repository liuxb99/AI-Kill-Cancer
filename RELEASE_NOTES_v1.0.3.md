# AI-Kill-Cancer v1.0.3

Release candidate date: 2026-08-10

## Focus

v1.0.3 consolidates the Local-First Research & Demo Showcase engineering milestone. The release keeps Local SQLite as the primary persistent research workspace, while Vercel remains a synthetic, ephemeral demonstration environment.

## Highlights

- Persistent Local SQLite workspace with integrity, backup/restore, restart persistence, and pre-upgrade backup.
- Controlled CSV import with validation, duplicate preview, explicit confirmation, no silent overwrite, and import history.
- Local Workspace Import UI with environment write guard.
- Synthetic PTC showcase cases with deterministic bootstrap and cross-route context continuity.
- Production API JSON smoke and multi-route Chromium verification.
- Restart E2E that verifies Case → Variant → Evidence → Recommendation → Clinical Decision traceability.

## Important boundary

This project is research software, not a medical device or clinical treatment system. Synthetic showcase content is not real patient evidence and must not be used as diagnosis, prescription, dosing, treatment, or efficacy guidance.

## Release condition

Create the v1.0.3 tag only after the latest Local Verification Gate and production deployment verification relevant to this release candidate are green. See `docs/RELEASE_CHECKLIST_v1.0.3.md`.
