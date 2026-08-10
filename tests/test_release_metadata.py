from pathlib import Path

from src.backend.config import settings


ROOT = Path(__file__).resolve().parents[1]


def _root_version() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def test_product_version_authorities_match():
    version = _root_version()
    assert version == "1.0.3"
    assert settings.APP_VERSION == version


def test_release_notes_and_checklist_match_product_version():
    version = _root_version()
    notes = ROOT / f"RELEASE_NOTES_v{version}.md"
    checklist = ROOT / "docs" / f"RELEASE_CHECKLIST_v{version}.md"

    assert notes.is_file(), f"missing release notes for {version}"
    assert checklist.is_file(), f"missing release checklist for {version}"

    notes_text = notes.read_text(encoding="utf-8")
    checklist_text = checklist.read_text(encoding="utf-8")
    assert f"v{version}" in notes_text
    assert f"v{version}" in checklist_text


def test_changelog_contains_current_product_version():
    version = _root_version()
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert version in changelog


def test_private_frontend_package_is_not_product_version_authority():
    package_json = (ROOT / "src" / "frontend" / "package.json").read_text(encoding="utf-8")
    assert '"private": true' in package_json
