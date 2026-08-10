from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_api_has_no_501_scaffold_endpoints():
    offenders: list[str] = []
    for path in (ROOT / "src/backend/api").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        if "status_code=501" in lowered or "http_501" in lowered or '"not_implemented"' in lowered:
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == [], f"Runtime 501/not_implemented API scaffolds remain: {offenders}"


def test_stable_adapter_modules_are_concrete():
    stable_modules = [
        "src/backend/adapters/civic.py",
        "src/backend/adapters/dgidb.py",
        "src/backend/adapters/ensembl_vep.py",
        "src/backend/adapters/opencravat.py",
        "src/backend/adapters/myvariant.py",
        "src/backend/adapters/oncotree.py",
        "src/backend/adapters/drkg.py",
        "src/backend/adapters/pharmcat.py",
    ]
    offenders = [path for path in stable_modules if "NotConfiguredAdapter" in _text(path)]
    assert offenders == [], f"Stable adapter modules still expose placeholders: {offenders}"


def test_variant_annotation_runtime_has_no_terminal_not_implemented_result():
    paths = [
        "src/backend/pipeline/vep_adapter.py",
        "src/backend/pipeline/opencravat_adapter.py",
    ]
    offenders = [path for path in paths if 'errors=["Not implemented"]' in _text(path)]
    assert offenders == [], f"Variant annotation runtime still has terminal stubs: {offenders}"


def test_release_critical_modules_do_not_contain_phase_placeholder_banner():
    paths = [
        "src/backend/adapters/civic.py",
        "src/backend/adapters/dgidb.py",
        "src/backend/adapters/ensembl_vep.py",
        "src/backend/adapters/opencravat.py",
        "src/backend/adapters/myvariant.py",
        "src/backend/adapters/oncotree.py",
        "src/backend/adapters/drkg.py",
        "src/backend/adapters/pharmcat.py",
    ]
    offenders: list[str] = []
    for path in paths:
        lowered = _text(path).lower()
        if "placeholder for phase" in lowered or "mvp (phase 1)" in lowered:
            offenders.append(path)
    assert offenders == [], f"Stale phase placeholder modules remain: {offenders}"
