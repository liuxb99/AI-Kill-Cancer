# v1.0.3 Release Checklist

更新日期：2026-08-10

## Version alignment
- [x] root `VERSION` = `1.0.3`
- [x] backend `Settings.APP_VERSION` = `1.0.3`
- [x] `CHANGELOG.md` includes 1.0.3
- [x] `RELEASE_NOTES_v1.0.3.md` exists
- [ ] verify no release-critical runtime metadata still reports 1.0.2

> `src/frontend/package.json` is a private frontend package and is not used as the product release authority. Product release authority is root `VERSION` + backend `APP_VERSION`.

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
- [x] production API JSON smoke
- [x] production multi-route Chromium synthetic gate
- [x] synthetic query propagation across major routes
- [x] DB cold-start recovery verified

## Release gates
- [x] Workspace Import UI baseline verified — Local Gate #152 PASS
- [ ] latest release-candidate Local Verification Gate PASS
- [ ] latest release-candidate CI/build checks PASS
- [ ] production deployment for release-candidate head PASS
- [ ] production API JSON smoke PASS on release-candidate head
- [ ] production multi-route Chromium gate PASS on release-candidate head

## Tagging policy
Do not create or move a `v1.0.3` tag until all unchecked release gates above are green. A green software release does not imply clinical validation.
