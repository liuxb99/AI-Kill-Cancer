"""
ClinicalReasoningService — orchestrates evidence-grounded clinical reasoning.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from src.backend.reasoning.context import ReasoningContextBuilder
from src.backend.reasoning.validator import EvidenceCitationValidator, HallucinationGuard
from src.backend.reasoning.conflicts import ConflictAnalyzer
from src.backend.reasoning.repository import ReasoningRunRepository
from src.backend.reasoning.llm import get_llm_adapter, LLMAdapter
from src.backend.reasoning.models import (
    ClinicalReasoningResult, ReasoningRunResponse, ReasoningDrugExplanation, SafetyNotice,
)

logger = logging.getLogger(__name__)


class ClinicalReasoningService:
    """
    Orchestrates evidence-grounded clinical reasoning.

    Steps:
    1. Build frozen context from evidence, ranking, knowledge snapshots
    2. Run ConflictAnalyzer on evidence
    3. Build structured prompt for LLM
    4. Call LLM adapter
    5. Parse structured response
    6. Validate citations with EvidenceCitationValidator
    7. Return result with status
    """

    def __init__(self, db, llm_adapter: Optional[LLMAdapter] = None,
                 config: Optional[dict] = None):
        self.db = db
        self.config = config or {}
        self.llm = llm_adapter or get_llm_adapter(self.config.get("llm", {}))
        self.context_builder = ReasoningContextBuilder()
        self.validator = EvidenceCitationValidator()
        self.guard = HallucinationGuard()
        self.conflict_analyzer = ConflictAnalyzer()
        self.repo = ReasoningRunRepository(db)
        self.prompt_template_version = "1.0.0"

    async def reason(
        self,
        case_id: str = "",
        variant_data: Optional[dict] = None,
        evidence_items: Optional[list[dict]] = None,
        ranking_result: Optional[dict] = None,
        knowledge_data: Optional[dict] = None,
        disease: str = "",
        gene_symbol: str = "",
        question: str = "",
    ) -> ReasoningRunResponse:
        """
        Run clinical reasoning for a case.

        Uses frozen context snapshots. All evidence must be pre-collected.
        """
        datetime.utcnow()
        run_id = uuid.uuid4()

        # Build frozen context
        context = await self.context_builder.build(
            variant_data=variant_data,
            evidence_items=evidence_items,
            ranking_result=ranking_result,
            knowledge_data=knowledge_data,
        )

        # Analyze conflicts
        conflicts = self.conflict_analyzer.analyze(evidence_items or [])

        # Collect drug names from evidence
        drug_names = list(set(
            str(item.get("drug_name", ""))
            for item in (evidence_items or [])
            if item.get("drug_name")
        ))

        # Collect all evidence IDs
        all_evidence_ids = list(set(
            str(item.get("id", ""))
            for item in (evidence_items or [])
            if item.get("id")
        ))

        # Load validator with snapshot
        self.validator.load_snapshot(evidence_items or [], drug_names)
        self.guard.load_snapshot(evidence_items or [])

        # Check LLM availability
        if not self.llm.is_available:
            # Return structured result without LLM
            result_id = str(uuid.uuid4())
            reasoning_result = ClinicalReasoningResult(
                id=result_id,
                case_id=case_id,
                user_question=question,
                summary=f"Clinical reasoning for {gene_symbol or 'variant'} - LLM not available.",
                key_findings=[f"Found {len(evidence_items or [])} evidence items for {gene_symbol or 'unknown gene'}"],
                supporting_evidence_ids=all_evidence_ids,
                drug_explanations=[
                    ReasoningDrugExplanation(
                        drug_name=d,
                        explanation="Evidence available but LLM not configured for explanation.",
                        supporting_evidence_ids=[],
                    ) for d in drug_names
                ],
                safety_notice=SafetyNotice(),
            )

            # Save run
            await self.repo.create(
                id=run_id,
                case_id=case_id or None,
                status="no_llm",
                provider=self.llm.provider,
                model="disabled",
                prompt_template_version=self.prompt_template_version,
                context_hash=context.context_hash,
                reasoning_data=reasoning_result.model_dump(),
            )

            return ReasoningRunResponse(
                run_id=str(run_id),
                status="no_llm",
                reasoning=reasoning_result,
                message="LLM not configured. Returning evidence summary without LLM reasoning.",
            )

        # Build structured prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            gene_symbol=gene_symbol,
            disease=disease,
            evidence_count=len(evidence_items or []),
            drug_count=len(drug_names),
            conflicts=conflicts,
            evidence_items=evidence_items or [],
            ranking_result=ranking_result,
            question=question,
        )

        input_hash = hashlib.sha256(
            (system_prompt + user_prompt).encode()
        ).hexdigest()

        # Call LLM
        llm_result = await self.llm.generate(user_prompt, system_prompt)

        if not llm_result.success:
            await self.repo.create(
                id=run_id,
                case_id=case_id or None,
                status="failed",
                provider=self.llm.provider,
                model=self.llm.model,
                prompt_template_version=self.prompt_template_version,
                temperature=self.llm.temperature,
                seed=self.llm.seed,
                input_hash=input_hash,
                token_usage=llm_result.token_usage,
                latency_ms=llm_result.latency_ms,
                context_hash=context.context_hash,
                reasoning_data={"error": llm_result.error},
            )
            return ReasoningRunResponse(
                run_id=str(run_id),
                status="failed",
                message=f"LLM call failed: {llm_result.error}",
            )

        # Parse structured result
        reasoning_result = self._parse_llm_output(llm_result.content, case_id, all_evidence_ids, drug_names)
        reasoning_result.user_question = question

        output_hash = hashlib.sha256(
            json.dumps(reasoning_result.model_dump(), sort_keys=True).encode()
        ).hexdigest()

        # Validate citations
        validation = self.validator.validate(reasoning_result)

        final_status = "rejected" if not validation.valid else "completed"

        # Save
        reasoning_result.id = str(uuid.uuid4())
        await self.repo.create(
            id=run_id,
            case_id=case_id or None,
            status=final_status,
            provider=self.llm.provider,
            model=self.llm.model,
            model_version=llm_result.model,
            prompt_template_version=self.prompt_template_version,
            temperature=self.llm.temperature,
            seed=self.llm.seed,
            input_hash=input_hash,
            output_hash=output_hash,
            token_usage=llm_result.token_usage,
            latency_ms=llm_result.latency_ms,
            context_hash=context.context_hash,
            reasoning_data=reasoning_result.model_dump(),
            validation_result=validation.model_dump() if not validation.valid else None,
        )

        return ReasoningRunResponse(
            run_id=str(run_id),
            status=final_status,
            reasoning=reasoning_result if final_status == "completed" else None,
            validation_result=validation if final_status == "rejected" else None,
            message="Reasoning completed" if final_status == "completed" else "Reasoning rejected due to citation validation failure",
        )

    def _build_system_prompt(self) -> str:
        return (
            "You are a clinical decision support assistant for precision oncology. "
            "Your role is to SUMMARIZE, EXPLAIN, and COMPARE evidence. "
            "You must NOT invent evidence, create PMIDs, fabricate drug names, "
            "or recommend specific dosages or treatment plans. "
            "You must NOT replace clinical judgment. "
            "Always cite evidence IDs when making claims. "
            "Acknowledge uncertainties and conflicting evidence. "
            "Respond in JSON format with the following structure: "
            "{summary, key_findings, supporting_evidence_ids, conflicting_evidence_ids, "
            "drug_explanations: [{drug_name, explanation, supporting_evidence_ids, limitations}], "
            "uncertainties, missing_information, limitations}"
        )

    def _build_user_prompt(self, gene_symbol: str, disease: str,
                            evidence_count: int, drug_count: int,
                            conflicts: list[dict],
                            evidence_items: list[dict],
                            ranking_result: Optional[dict] = None,
                            question: str = "") -> str:
        """Build the user prompt with evidence context and user question."""
        prompt_parts = [
            f"Gene: {gene_symbol or 'N/A'}",
            f"Disease: {disease or 'N/A'}",
            f"Evidence items found: {evidence_count}",
            f"Drugs mentioned: {drug_count}",
        ]

        if question:
            prompt_parts.append(f"\nUser question: {question}")

        if conflicts:
            prompt_parts.append("\nConflicts detected:")
            for c in conflicts:
                prompt_parts.append(
                    f"- {c['drug_name']}: {c['supporting_count']} supporting vs {c['conflicting_count']} conflicting ({c['severity']} severity)"
                )

        if evidence_items:
            prompt_parts.append("\nEvidence summary:")
            for item in evidence_items[:20]:  # Limit to 20 items
                eid = item.get("id", "?")
                drug = item.get("drug_name", "?")
                direction = item.get("evidence_direction", "?")
                level = item.get("evidence_level", "?")
                prompt_parts.append(f"- [{eid}] {drug}: {direction} (level {level})")

        if ranking_result and ranking_result.get("rankings"):
            prompt_parts.append("\nDrug rankings:")
            for drug in ranking_result["rankings"][:5]:
                prompt_parts.append(f"- {drug.get('drug_name', '?')}: score {drug.get('total_score', 0)}")

        return "\n".join(prompt_parts)

    def _parse_llm_output(self, content: str, case_id: str,
                           all_evidence_ids: list[str],
                           drug_names: list[str]) -> ClinicalReasoningResult:
        """Parse LLM JSON output into structured result."""
        try:
            # Try to find JSON in the response
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                data = json.loads(json_str)
            else:
                data = {}
        except (json.JSONDecodeError, ValueError):
            data = {}

        drug_explanations = []
        for de in data.get("drug_explanations", []):
            drug_explanations.append(ReasoningDrugExplanation(
                drug_name=de.get("drug_name", ""),
                explanation=de.get("explanation", ""),
                supporting_evidence_ids=de.get("supporting_evidence_ids", []),
                conflicting_evidence_ids=de.get("conflicting_evidence_ids", []),
                limitations=de.get("limitations", []),
            ))

        return ClinicalReasoningResult(
            case_id=case_id,
            summary=data.get("summary", ""),
            key_findings=data.get("key_findings", []),
            supporting_evidence_ids=data.get("supporting_evidence_ids", all_evidence_ids),
            conflicting_evidence_ids=data.get("conflicting_evidence_ids", []),
            drug_explanations=drug_explanations,
            uncertainties=data.get("uncertainties", []),
            missing_information=data.get("missing_information", []),
            limitations=data.get("limitations", []),
            safety_notice=SafetyNotice(),
        )
