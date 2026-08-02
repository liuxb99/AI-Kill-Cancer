"""Apply Phase 3G treatment-plan safety integration.

Idempotent helper used only by the validation workflow.  It is removed before
merge after the generated service change has been committed.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "src/backend/services/treatment_plan_service.py"


def replace_once(old: str, new: str) -> None:
    text = SERVICE.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError("Expected treatment-plan service block was not found")
    SERVICE.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    replace_once(
        "from src.backend.clinical.treatment_plan_rules import TreatmentPlanRuleSet\n",
        "from src.backend.clinical.treatment_plan_rules import TreatmentPlanRuleSet\n"
        "from src.backend.clinical.treatment_plan_safety_gate import (\n"
        "    SafetyGateReport,\n"
        "    TreatmentPlanSafetyGate,\n"
        ")\n",
    )
    replace_once(
        "        self._state_machine = state_machine\n",
        "        self._state_machine = state_machine\n"
        "        self._safety_gate = TreatmentPlanSafetyGate()\n",
    )
    replace_once(
        "    # ── Public API: Status Transitions ─────────────────────────────────────\n\n"
        "    async def _transition_status(\n",
        "    # ── Public API: Clinical Safety Readiness ──────────────────────────────\n\n"
        "    async def get_safety_gate(\n"
        "        self,\n"
        "        plan_id: str,\n"
        "        target_status: str,\n"
        "    ) -> SafetyGateReport:\n"
        "        \"\"\"Return a deterministic approval/activation readiness report.\"\"\"\n"
        "        model = await self._plan_repo.get_current_by_plan_id(plan_id)\n"
        "        if model is None:\n"
        "            raise ValueError(f\"Treatment plan with id '{plan_id}' not found\")\n"
        "        return self._safety_gate.evaluate(model, target_status)\n\n"
        "    # ── Public API: Status Transitions ─────────────────────────────────────\n\n"
        "    async def _transition_status(\n",
    )
    replace_once(
        "        current_status = PlanStatus(model.plan_status)\n"
        "        self._state_machine.transition(current_status, target_status)\n\n"
        "        now = datetime.now(timezone.utc).replace(tzinfo=None)\n",
        "        current_status = PlanStatus(model.plan_status)\n"
        "        self._state_machine.transition(current_status, target_status)\n\n"
        "        # Approval and activation are clinical safety boundaries.  Evaluate\n"
        "        # the materialised aggregate before mutating status or timestamps.\n"
        "        if target_status in {PlanStatus.APPROVED, PlanStatus.ACTIVE}:\n"
        "            self._safety_gate.assert_can_transition(model, target_status.value)\n\n"
        "        now = datetime.now(timezone.utc).replace(tzinfo=None)\n",
    )


if __name__ == "__main__":
    main()
