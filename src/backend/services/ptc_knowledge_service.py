"""PTC public therapy and clinical-trial knowledge ingestion."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any
from urllib.parse import quote

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.domain.ptc_knowledge import (
    PTCClinicalTrialModel,
    PTCEvidenceRecordModel,
    PTCTherapyModel,
    PTCTherapyTargetModel,
)

CTGOV_STUDIES_URL = "https://clinicaltrials.gov/api/v2/studies"
OPENFDA_LABEL_URL = "https://api.fda.gov/drug/label.json"

GENE_TERMS = ("BRAF", "RET", "NTRK1", "NTRK2", "NTRK3", "RAS", "NRAS", "HRAS", "KRAS", "TERT", "TP53")
DRUG_TARGETS: dict[str, list[tuple[str, str | None]]] = {
    "selpercatinib": [("RET", "fusion")],
    "pralsetinib": [("RET", "fusion")],
    "larotrectinib": [("NTRK1", "fusion"), ("NTRK2", "fusion"), ("NTRK3", "fusion")],
    "repotrectinib": [("NTRK1", "fusion"), ("NTRK2", "fusion"), ("NTRK3", "fusion")],
    "dabrafenib": [("BRAF", "V600E")],
    "trametinib": [("BRAF", "V600E")],
    "vemurafenib": [("BRAF", "V600E")],
    "lenvatinib": [("RET", None)],
    "sorafenib": [("BRAF", None), ("RET", None)],
    "cabozantinib": [("RET", None)],
}


def _first(value: Any) -> str | None:
    if isinstance(value, list):
        return str(value[0]) if value else None
    return str(value) if value is not None else None


def _key(*parts: str | None) -> str:
    raw = "|".join((part or "").strip().lower() for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def infer_target_genes(*values: Any) -> list[str]:
    text = " ".join(str(value) for value in values if value).upper()
    found: set[str] = set()
    for term in GENE_TERMS:
        if term in text:
            found.add(term)
    if "NTRK" in text:
        found.update({"NTRK1", "NTRK2", "NTRK3"})
    return sorted(found)


class PTCKnowledgeService:
    """Synchronize public knowledge while keeping transaction ownership in Service."""

    def __init__(self, db: AsyncSession, client: httpx.AsyncClient | None = None):
        self.db = db
        self.client = client

    async def _http(self) -> httpx.AsyncClient:
        if self.client is not None:
            return self.client
        return httpx.AsyncClient(timeout=45.0, follow_redirects=True)

    async def sync_clinical_trials(self, *, page_size: int = 100) -> int:
        client = await self._http()
        owned = self.client is None
        try:
            response = await client.get(
                CTGOV_STUDIES_URL,
                params={
                    "query.cond": "Papillary Thyroid Carcinoma",
                    "pageSize": min(max(page_size, 1), 1000),
                    "format": "json",
                },
            )
            response.raise_for_status()
            count = 0
            for study in response.json().get("studies", []):
                protocol = study.get("protocolSection", {})
                identification = protocol.get("identificationModule", {})
                status = protocol.get("statusModule", {})
                design = protocol.get("designModule", {})
                conditions = protocol.get("conditionsModule", {})
                arms = protocol.get("armsInterventionsModule", {})
                eligibility = protocol.get("eligibilityModule", {})
                contacts = protocol.get("contactsLocationsModule", {})
                nct_id = identification.get("nctId")
                if not nct_id:
                    continue
                existing = await self.db.scalar(
                    select(PTCClinicalTrialModel).where(PTCClinicalTrialModel.nct_id == nct_id)
                )
                model = existing or PTCClinicalTrialModel(nct_id=nct_id)
                model.brief_title = identification.get("briefTitle") or nct_id
                model.official_title = identification.get("officialTitle")
                model.overall_status = status.get("overallStatus")
                model.phases = design.get("phases", [])
                model.study_type = design.get("studyType")
                model.conditions = conditions.get("conditions", [])
                model.interventions = [
                    {
                        "name": item.get("name"),
                        "type": item.get("type"),
                        "description": item.get("description"),
                    }
                    for item in arms.get("interventions", [])
                ]
                model.target_genes = infer_target_genes(
                    model.brief_title,
                    model.official_title,
                    model.conditions,
                    model.interventions,
                    eligibility.get("eligibilityCriteria"),
                )
                model.eligibility = eligibility.get("eligibilityCriteria")
                enrollment = design.get("enrollmentInfo", {})
                model.enrollment = enrollment.get("count")
                model.locations = [
                    {
                        "facility": item.get("facility"),
                        "city": item.get("city"),
                        "state": item.get("state"),
                        "country": item.get("country"),
                    }
                    for item in contacts.get("locations", [])
                ]
                model.start_date = status.get("startDateStruct", {}).get("date")
                model.completion_date = status.get("completionDateStruct", {}).get("date")
                model.last_update_posted = status.get("studyFirstPostDateStruct", {}).get("date")
                model.source_url = f"https://clinicaltrials.gov/study/{nct_id}"
                model.source_version = "api-v2"
                model.retrieved_at = datetime.utcnow()
                if existing is None:
                    self.db.add(model)
                count += 1
            await self.db.commit()
            return count
        except Exception:
            await self.db.rollback()
            raise
        finally:
            if owned:
                await client.aclose()

    async def sync_openfda_labels(self, drug_names: list[str]) -> int:
        client = await self._http()
        owned = self.client is None
        try:
            count = 0
            for drug_name in sorted({name.strip() for name in drug_names if name.strip()}):
                search = f'openfda.generic_name:"{drug_name}"'
                response = await client.get(OPENFDA_LABEL_URL, params={"search": search, "limit": 10})
                if response.status_code == 404:
                    continue
                response.raise_for_status()
                for record in response.json().get("results", []):
                    openfda = record.get("openfda", {})
                    label_id = record.get("id") or record.get("set_id") or _key(drug_name, record.get("effective_time"))
                    existing = await self.db.scalar(
                        select(PTCTherapyModel).where(
                            PTCTherapyModel.source_name == "openFDA",
                            PTCTherapyModel.source_record_id == label_id,
                        )
                    )
                    model = existing or PTCTherapyModel(
                        therapy_key=f"openfda:{label_id}", source_name="openFDA", source_record_id=label_id
                    )
                    model.name = _first(openfda.get("brand_name")) or drug_name
                    model.generic_name = _first(openfda.get("generic_name")) or drug_name
                    model.therapy_type = "drug"
                    model.approval_status = "FDA label available"
                    model.indications = record.get("indications_and_usage", [])
                    model.mechanism = _first(record.get("mechanism_of_action"))
                    model.dosage_and_administration = _first(record.get("dosage_and_administration"))
                    model.warnings = record.get("boxed_warning", []) + record.get("warnings", []) + record.get("warnings_and_cautions", [])
                    model.source_url = f"https://api.fda.gov/drug/label.json?search=id:{quote(label_id)}"
                    model.source_version = record.get("effective_time")
                    model.retrieved_at = datetime.utcnow()
                    if existing is None:
                        self.db.add(model)
                    await self.db.flush()
                    await self.db.execute(delete(PTCTherapyTargetModel).where(PTCTherapyTargetModel.therapy_id == model.id))
                    generic = (model.generic_name or drug_name).lower()
                    targets = DRUG_TARGETS.get(generic, [])
                    if not targets:
                        targets = [(gene, None) for gene in infer_target_genes(model.mechanism, model.indications)]
                    for gene, variant in targets:
                        self.db.add(
                            PTCTherapyTargetModel(
                                therapy_id=model.id,
                                gene_symbol=gene,
                                variant=variant,
                                target_type="molecular_target",
                                interaction_type="inhibits_or_targets",
                                evidence_level="label_or_curated_mapping",
                                source_record_id=label_id,
                            )
                        )
                    count += 1
            await self.db.commit()
            return count
        except Exception:
            await self.db.rollback()
            raise
        finally:
            if owned:
                await client.aclose()

    async def create_evidence(
        self,
        *,
        source_name: str,
        source_record_id: str,
        evidence_type: str,
        title: str | None = None,
        summary: str | None = None,
        evidence_level: str | None = None,
        direction: str | None = None,
        gene_symbol: str | None = None,
        variant: str | None = None,
        therapy_id: str | None = None,
        clinical_trial_id: str | None = None,
        publication_id: str | None = None,
        citation: str | None = None,
        source_url: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> PTCEvidenceRecordModel:
        evidence_key = _key(source_name, source_record_id, gene_symbol, variant)
        existing = await self.db.scalar(
            select(PTCEvidenceRecordModel).where(PTCEvidenceRecordModel.evidence_key == evidence_key)
        )
        model = existing or PTCEvidenceRecordModel(
            evidence_key=evidence_key, source_name=source_name, source_record_id=source_record_id
        )
        model.evidence_type = evidence_type
        model.title = title
        model.summary = summary
        model.evidence_level = evidence_level
        model.direction = direction
        model.gene_symbol = gene_symbol.upper() if gene_symbol else None
        model.variant = variant
        model.therapy_id = therapy_id
        model.clinical_trial_id = clinical_trial_id
        model.publication_id = publication_id
        model.citation = citation
        model.source_url = source_url
        model.payload = payload or {}
        model.retrieved_at = datetime.utcnow()
        if existing is None:
            self.db.add(model)
        await self.db.commit()
        await self.db.refresh(model)
        return model


__all__ = [
    "PTCKnowledgeService",
    "CTGOV_STUDIES_URL",
    "OPENFDA_LABEL_URL",
    "infer_target_genes",
    "DRUG_TARGETS",
]
