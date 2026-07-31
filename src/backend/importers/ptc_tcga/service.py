"""Transactional import service for the first TCGA-THCA end-to-end slice."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.domain.clinical_graph_outbox import ClinicalGraphOutboxModel
from src.backend.domain.ptc_research import (
    PTCImportBatchModel,
    PTCOutcomeModel,
    PTCResearchCaseInput,
    PTCResearchCaseModel,
    PTCVariantModel,
)
from src.backend.importers.ptc_tcga.normalizer import normalize_case_record


@dataclass(frozen=True)
class PTCImportResult:
    batch_id: str
    imported_cases: int
    imported_variants: int
    imported_outcomes: int
    outbox_events: int


class PTCTCGAImportService:
    """Import normalized PTC research records in one service-owned transaction."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def import_records(
        self,
        records: Iterable[Mapping[str, Any] | PTCResearchCaseInput],
        *,
        source_version: str | None = None,
        batch_id: str | None = None,
    ) -> PTCImportResult:
        normalized = [
            record if isinstance(record, PTCResearchCaseInput) else normalize_case_record(record)
            for record in records
        ]
        if not normalized:
            raise ValueError("PTC import requires at least one record")

        batch_id = batch_id or f"ptc-{uuid.uuid4()}"
        checksum = hashlib.sha256(
            json.dumps(
                [item.model_dump(mode="json") for item in normalized],
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        batch = PTCImportBatchModel(
            batch_id=batch_id,
            source_dataset=normalized[0].source_dataset,
            source_version=source_version,
            status="running",
            checksum=checksum,
        )
        self.db.add(batch)

        cases = variants = outcomes = events = 0
        try:
            for item in normalized:
                case = await self._upsert_case(item)
                cases += 1
                events += await self._write_case_event(item)

                for variant_input in item.variants:
                    variant = await self._upsert_variant(case, item, variant_input)
                    if variant is not None:
                        variants += 1
                    events += await self._write_variant_event(item, variant_input)

                for outcome_input in item.outcomes:
                    outcome = await self._upsert_outcome(case, item, outcome_input)
                    if outcome is not None:
                        outcomes += 1
                    events += await self._write_outcome_event(item, outcome_input)

            batch.status = "completed"
            batch.record_count = cases
            batch.completed_at = datetime.utcnow()
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        return PTCImportResult(
            batch_id=batch_id,
            imported_cases=cases,
            imported_variants=variants,
            imported_outcomes=outcomes,
            outbox_events=events,
        )

    async def _upsert_case(self, item: PTCResearchCaseInput) -> PTCResearchCaseModel:
        result = await self.db.execute(
            select(PTCResearchCaseModel).where(
                PTCResearchCaseModel.source_dataset == item.source_dataset,
                PTCResearchCaseModel.case_id == item.case_id,
            )
        )
        model = result.scalar_one_or_none()
        values = item.model_dump(exclude={"variants", "outcomes"})
        if model is None:
            model = PTCResearchCaseModel(**values)
            self.db.add(model)
        else:
            for key, value in values.items():
                setattr(model, key, value)
        await self.db.flush()
        return model

    async def _upsert_variant(self, case, item, variant_input):
        variant_id = variant_input.variant_id
        if variant_id is None:
            raise ValueError(f"Variant for {item.case_id} has no deterministic variant_id")
        result = await self.db.execute(
            select(PTCVariantModel).where(
                PTCVariantModel.source_dataset == item.source_dataset,
                PTCVariantModel.variant_id == variant_id,
            )
        )
        model = result.scalar_one_or_none()
        values = variant_input.model_dump()
        if model is None:
            model = PTCVariantModel(
                **values,
                research_case_id=case.id,
                case_id=item.case_id,
                source_dataset=item.source_dataset,
            )
            self.db.add(model)
        else:
            for key, value in values.items():
                setattr(model, key, value)
            model.research_case_id = case.id
            model.case_id = item.case_id
        await self.db.flush()
        return model

    async def _upsert_outcome(self, case, item, outcome_input):
        outcome_id = outcome_input.outcome_id or f"{item.case_id}:{outcome_input.outcome_type}"
        result = await self.db.execute(
            select(PTCOutcomeModel).where(
                PTCOutcomeModel.source_dataset == item.source_dataset,
                PTCOutcomeModel.outcome_id == outcome_id,
            )
        )
        model = result.scalar_one_or_none()
        values = outcome_input.model_dump(exclude={"outcome_id"})
        if model is None:
            model = PTCOutcomeModel(
                outcome_id=outcome_id,
                **values,
                research_case_id=case.id,
                case_id=item.case_id,
                source_dataset=item.source_dataset,
            )
            self.db.add(model)
        else:
            for key, value in values.items():
                setattr(model, key, value)
        await self.db.flush()
        return model

    async def _put_event(self, *, event_id: str, event_type: str, aggregate_type: str, aggregate_id: str, payload: dict, correlation_id: str) -> int:
        existing = await self.db.execute(
            select(ClinicalGraphOutboxModel.id).where(ClinicalGraphOutboxModel.event_id == event_id)
        )
        if existing.scalar_one_or_none() is not None:
            return 0
        self.db.add(
            ClinicalGraphOutboxModel(
                event_id=event_id,
                event_type=event_type,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                schema_version=1,
                payload=payload,
                correlation_id=correlation_id,
                occurred_at=datetime.utcnow(),
            )
        )
        await self.db.flush()
        return 1

    async def _write_case_event(self, item: PTCResearchCaseInput) -> int:
        event_id = f"ptc-case:{item.source_dataset}:{item.case_id}:v1"
        return await self._put_event(
            event_id=event_id,
            event_type="ptc_case.created",
            aggregate_type="ptc_research_case",
            aggregate_id=item.case_id,
            correlation_id=item.case_id,
            payload={
                "case_id": item.case_id,
                "disease": "papillary_thyroid_carcinoma",
                "stage": item.pathologic_stage,
                "sex": item.sex,
                "source_dataset": item.source_dataset,
                "source_record_id": item.source_record_id,
            },
        )

    async def _write_variant_event(self, item, variant) -> int:
        event_id = f"ptc-variant:{item.source_dataset}:{variant.variant_id}:v1"
        return await self._put_event(
            event_id=event_id,
            event_type="ptc_variant.observed",
            aggregate_type="ptc_variant",
            aggregate_id=variant.variant_id or "",
            correlation_id=item.case_id,
            payload={
                "case_id": item.case_id,
                "variant_id": variant.variant_id,
                "gene": variant.gene,
                "chromosome": variant.chromosome,
                "position": variant.position,
                "reference": variant.reference,
                "alternate": variant.alternate,
                "protein_change": variant.protein_change,
                "classification": variant.classification,
                "source_dataset": item.source_dataset,
                "source_record_id": variant.source_record_id,
            },
        )

    async def _write_outcome_event(self, item, outcome) -> int:
        outcome_id = outcome.outcome_id or f"{item.case_id}:{outcome.outcome_type}"
        event_id = f"ptc-outcome:{item.source_dataset}:{outcome_id}:v1"
        return await self._put_event(
            event_id=event_id,
            event_type="ptc_outcome.recorded",
            aggregate_type="ptc_outcome",
            aggregate_id=outcome_id,
            correlation_id=item.case_id,
            payload={
                "case_id": item.case_id,
                "outcome_id": outcome_id,
                "outcome_type": outcome.outcome_type,
                "outcome_value": outcome.outcome_value,
                "observed_at": outcome.observed_at.isoformat() if outcome.observed_at else None,
                "source_dataset": item.source_dataset,
                "source_record_id": outcome.source_record_id,
            },
        )


__all__ = ["PTCTCGAImportService", "PTCImportResult"]
