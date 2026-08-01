"""Evidence-grounded PTC research assistant.

This endpoint does not call an LLM. It deterministically assembles de-identified
research-case facts, molecular targeting records, publications, and trials into
an auditable answer with source links and UI navigation actions.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.api.v1.ptc_targeting import GENE_TARGET_CATALOG
from src.backend.database.session import get_db
from src.backend.domain.ptc_knowledge import (
    PTCClinicalTrialModel,
    PTCEvidenceRecordModel,
    PTCTherapyModel,
)
from src.backend.domain.ptc_research import PTCResearchCaseModel

router = APIRouter(prefix="/ptc-assistant", tags=["ptc-assistant"])


class PTCAssistantRequest(BaseModel):
    case_id: str = Field(min_length=1, max_length=128)
    question: str = Field(min_length=2, max_length=2000)
    gene: str | None = Field(default=None, max_length=32)


def _question_intent(question: str) -> str:
    text = question.lower()
    if any(term in text for term in ("trial", "试验", "試驗", "招募")):
        return "clinical_trials"
    if any(term in text for term in ("figure", "table", "图", "圖", "表格", "论文", "論文", "文献", "文獻")):
        return "literature"
    if any(term in text for term in ("drug", "therapy", "药", "藥", "治疗", "治療", "推荐", "推薦")):
        return "therapy"
    if any(term in text for term in ("protein", "structure", "residue", "蛋白", "结构", "結構", "残基", "殘基")):
        return "structure"
    return "overview"


def _pick_gene(requested: str | None, question: str, available: list[str]) -> str | None:
    if requested:
        return requested.strip().upper()
    upper = question.upper()
    for gene in available:
        if gene in upper:
            return gene
    return available[0] if available else None


def _evidence_payload(item: PTCEvidenceRecordModel) -> dict[str, Any]:
    payload = item.payload if isinstance(item.payload, dict) else {}
    return {
        "evidence_key": item.evidence_key,
        "source": item.source_name,
        "title": item.title,
        "summary": item.summary,
        "level": item.evidence_level,
        "direction": item.direction,
        "publication_id": item.publication_id,
        "url": item.source_url,
        "figures": payload.get("figures", []),
        "tables": payload.get("tables", []),
        "pmcid": payload.get("pmcid"),
    }


@router.post("/ask")
async def ask_ptc_assistant(body: PTCAssistantRequest, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    case = await db.scalar(
        select(PTCResearchCaseModel)
        .where(PTCResearchCaseModel.case_id == body.case_id)
        .options(
            selectinload(PTCResearchCaseModel.variants),
            selectinload(PTCResearchCaseModel.outcomes),
        )
    )
    if case is None:
        raise HTTPException(status_code=404, detail="PTC research case not found")

    genes = sorted({variant.gene.upper() for variant in case.variants})
    gene = _pick_gene(body.gene, body.question, genes)
    intent = _question_intent(body.question)
    variants = [
        {
            "variant_id": item.variant_id,
            "gene": item.gene,
            "protein_change": item.protein_change,
            "classification": item.classification,
        }
        for item in case.variants
        if gene is None or item.gene.upper() == gene
    ]

    therapies: list[PTCTherapyModel] = []
    evidence: list[PTCEvidenceRecordModel] = []
    trials: list[PTCClinicalTrialModel] = []
    if gene:
        therapy_rows = list((await db.execute(
            select(PTCTherapyModel)
            .options(selectinload(PTCTherapyModel.targets))
            .order_by(PTCTherapyModel.name)
        )).scalars().unique())
        therapies = [
            row for row in therapy_rows
            if any(target.gene_symbol.upper() == gene for target in row.targets)
        ][:20]
        evidence = list((await db.execute(
            select(PTCEvidenceRecordModel)
            .where(PTCEvidenceRecordModel.gene_symbol == gene)
            .order_by(PTCEvidenceRecordModel.created_at.desc())
            .limit(30)
        )).scalars())
        trials = list((await db.execute(
            select(PTCClinicalTrialModel)
            .where(or_(
                PTCClinicalTrialModel.brief_title.ilike(f"%{gene}%"),
                PTCClinicalTrialModel.official_title.ilike(f"%{gene}%"),
            ))
            .order_by(PTCClinicalTrialModel.nct_id)
            .limit(20)
        )).scalars())

    pathway = GENE_TARGET_CATALOG.get(gene or "", {})
    mutation_text = ", ".join(
        item["protein_change"] or item["variant_id"] for item in variants
    ) or "no imported protein change"
    therapy_names = [item.name for item in therapies]
    evidence_count = len(evidence)
    trial_count = len(trials)

    answer_parts = [
        f"Research case {case.case_id} is a de-identified {case.source_dataset} record.",
        f"The selected molecular focus is {gene or 'not available'}; imported change(s): {mutation_text}.",
    ]
    if pathway:
        answer_parts.append(
            f"The curated research pathway is {pathway.get('pathway')}, with protein domain "
            f"{pathway.get('protein_domain')}."
        )
    if therapy_names:
        answer_parts.append(
            "Persisted therapy records linked to this gene include " + ", ".join(therapy_names[:8]) + "."
        )
    else:
        classes = pathway.get("therapy_classes", []) if pathway else []
        if classes:
            answer_parts.append(
                "No persisted therapy record is currently available; curated research classes include "
                + ", ".join(classes) + "."
            )
    answer_parts.append(
        f"The database currently contains {evidence_count} linked evidence record(s) and "
        f"{trial_count} matching clinical-trial record(s)."
    )
    if intent == "literature":
        full_text_count = sum(
            1 for item in evidence
            if isinstance(item.payload, dict) and (item.payload.get("figures") or item.payload.get("tables"))
        )
        answer_parts.append(f"{full_text_count} evidence record(s) contain extracted PMC figures or tables.")
    answer_parts.append(
        "This is research decision support only. It does not establish clinical efficacy, eligibility, dosage, or a treatment prescription."
    )

    citations = [_evidence_payload(item) for item in evidence[:12]]
    actions: list[dict[str, Any]] = []
    if gene:
        actions.extend([
            {"type": "open_3d", "label": f"Open {gene} protein 3D", "gene": gene},
            {"type": "open_targeting", "label": f"Open {gene} targeting chain", "gene": gene},
            {"type": "open_literature", "label": f"Open {gene} figures and tables", "gene": gene},
        ])
    for item in trials[:3]:
        actions.append({
            "type": "open_trial",
            "label": f"Open {item.nct_id}",
            "url": item.source_url,
            "nct_id": item.nct_id,
        })

    return {
        "case_id": case.case_id,
        "question": body.question,
        "intent": intent,
        "selected_gene": gene,
        "answer": " ".join(answer_parts),
        "case_facts": {
            "source_dataset": case.source_dataset,
            "pathologic_stage": case.pathologic_stage,
            "tnm": [case.t_status, case.n_status, case.m_status],
            "vital_status": case.vital_status,
            "genes": genes,
            "variants": variants,
            "outcomes": [
                {"type": item.outcome_type, "value": item.outcome_value}
                for item in case.outcomes
            ],
        },
        "pathway": pathway,
        "therapies": [
            {
                "therapy_key": item.therapy_key,
                "name": item.name,
                "approval_status": item.approval_status,
                "mechanism": item.mechanism,
                "source": item.source_name,
                "url": item.source_url,
            }
            for item in therapies
        ],
        "evidence": citations,
        "trials": [
            {
                "nct_id": item.nct_id,
                "title": item.brief_title,
                "status": item.overall_status,
                "phases": item.phases,
                "url": item.source_url,
            }
            for item in trials
        ],
        "actions": actions,
        "trace": [
            {"step": 1, "name": "resolve_case", "records": 1},
            {"step": 2, "name": "resolve_gene_and_variants", "records": len(variants)},
            {"step": 3, "name": "resolve_therapies", "records": len(therapies)},
            {"step": 4, "name": "resolve_evidence", "records": len(evidence)},
            {"step": 5, "name": "resolve_trials", "records": len(trials)},
            {"step": 6, "name": "compose_auditable_answer", "records": 1},
        ],
        "disclaimer": "For research and education only; not medical advice or a treatment recommendation.",
    }


__all__ = ["router", "PTCAssistantRequest"]
