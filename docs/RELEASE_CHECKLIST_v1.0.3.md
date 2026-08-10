# v1.0.3 Release Checklist

更新日期：2026-08-10

## Version alignment
- [x] root `VERSION` = `1.0.3`
- [x] backend `Settings.APP_VERSION` = `1.0.3`
- [x] `CHANGELOG.md` includes 1.0.3
- [x] `RELEASE_NOTES_v1.0.3.md` exists
- [x] release-critical runtime metadata scan completed; no runtime authority still reports 1.0.2
- [x] automated `tests/test_release_metadata.py` added to Local Verification Gate

> `src/frontend/package.json` / `package-lock.json` are private frontend package metadata and are not product release authorities. Product release authority is root `VERSION` + backend `APP_VERSION`.

## Local-first acceptance
- [x] SQLite schema bootstrap / FK / busy timeout
- [x] integrity check
- [x] backup / atomic restore
- [x] restart persistence
- [x] pre-upgrade automatic backup
- [x] controlled CSV import v1
- [x] duplicate-aware preview + import history v2
- [x] Workspace Import UI + local-mode write guard
- [x] traceability restart E2E

## Vercel demo acceptance
- [x] deterministic synthetic CSV bootstrap
- [x] demo dataset validator
- [x] previous production API JSON smoke
- [x] previous production multi-route Chromium synthetic gate
- [x] synthetic query propagation across major routes
- [x] DB cold-start recovery verified

## Release gates
- [x] Workspace Import UI baseline verified — Local Gate #152 PASS
- [x] quota-hardening baseline verified — Local Gate #162 PASS
- [ ] latest metadata-consistency release-candidate Local Verification Gate PASS
- [ ] production deployment for release-candidate head PASS — currently blocked by Vercel daily free-tier deployment quota
- [ ] production API JSON smoke PASS on release-candidate head
- [ ] production multi-route Chromium gate PASS on release-candidate head

## External blocker

Latest production workflow reached `vercel deploy --prod` after token/project/environment preflight, then Vercel returned `api-deployments-free-per-day` / `Resource is limited - try again in 24 hours`. This is an external quota blocker, not an application build/runtime failure. Do not create no-op commits to retry deployments.

## Tagging policy
Do not create or move a `v1.0.3` tag until all unchecked release gates above are green. A green software release does not imply clinical validation.
