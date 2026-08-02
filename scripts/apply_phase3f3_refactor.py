"""Apply the Phase 3F-3 recommendation/report dependency refactor.

The script is intentionally idempotent so the validation workflow can execute
it safely on every PR synchronization.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"Expected source block not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_all(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        return
    path.write_text(text.replace(old, new), encoding="utf-8")


def main() -> None:
    service = ROOT / "src/backend/services/recommendation_service.py"
    report = ROOT / "src/backend/clinical/report_generator.py"

    replace_once(
        service,
        "from src.backend.clinical.report_generator import ReportGenerator\n",
        "from src.backend.clinical.report_generator import ReportGenerator\n"
        "from src.backend.contracts.recommendation_report import RecommendationReport\n",
    )
    replace_once(
        service,
        "        try:\n"
        "            from src.backend.api.v1.recommendation import RecommendationResponse\n\n"
        "            # Build a temporary RecommendationResponse for the ReportGenerator\n"
        "            resp = RecommendationResponse(**response)\n",
        "        try:\n"
        "            # Build a framework-independent report input.  API/Pydantic models\n"
        "            # must never flow back into the service or clinical layers.\n"
        "            resp = RecommendationReport.from_mapping(response)\n",
    )

    replace_once(
        report,
        "from typing import TYPE_CHECKING, Any\n\n"
        "if TYPE_CHECKING:\n"
        "    from src.backend.api.v1.recommendation import (\n"
        "        RecommendationDrugItem,\n"
        "        RecommendationResponse,\n"
        "    )\n",
        "from typing import Any\n\n"
        "from src.backend.contracts.recommendation_report import (\n"
        "    RecommendationDrugView,\n"
        "    RecommendationReportView,\n"
        ")\n",
    )
    replace_all(report, "RecommendationResponse", "RecommendationReportView")
    replace_all(report, "RecommendationDrugItem", "RecommendationDrugView")


if __name__ == "__main__":
    main()
