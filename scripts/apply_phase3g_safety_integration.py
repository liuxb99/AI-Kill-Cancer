"""Apply Phase 3G treatment-plan safety integration.

Idempotent helper used only by the validation workflow. It is removed before
merge after the generated service and regression-test changes are committed.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "src/backend/services/treatment_plan_service.py"
SERVICE_TEST = ROOT / "tests/backend/services/test_treatment_plan_service.py"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if path == SERVICE and "self._safety_gate.assert_can_transition" in text:
        return
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"Expected source block was not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    replace_once(
        SERVICE,
        "from src.backend.clinical.treatment_plan_rules import TreatmentPlanRuleSet\n",
        "from src.backend.clinical.treatment_plan_rules import TreatmentPlanRuleSet\n"
        "from src.backend.clinical.treatment_plan_safety_gate import (\n"
        "    SafetyGateReport,\n"
        "    TreatmentPlanSafetyGate,\n"
        ")\n",
    )
    replace_once(
        SERVICE,
        "        self._state_machine = state_machine\n",
        "        self._state_machine = state_machine\n"
        "        self._safety_gate = TreatmentPlanSafetyGate()\n",
    )
    replace_once(
        SERVICE,
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
        SERVICE,
        "        current_status = PlanStatus(model.plan_status)\n"
        "        self._state_machine.transition(current_status, target_status)\n\n"
        "        now = datetime.now(timezone.utc).replace(tzinfo=None)\n",
        "        current_status = PlanStatus(model.plan_status)\n"
        "        self._state_machine.transition(current_status, target_status)\n\n"
        "        # Approval and activation are clinical safety boundaries. Evaluate\n"
        "        # the materialised aggregate before mutating status or timestamps.\n"
        "        if target_status in {PlanStatus.APPROVED, PlanStatus.ACTIVE}:\n"
        "            self._safety_gate.assert_can_transition(model, target_status.value)\n\n"
        "        now = datetime.now(timezone.utc).replace(tzinfo=None)\n",
    )
    replace_once(
        SERVICE_TEST,
        "        self._plan_model = _make_plan_model(plan_id=\"plan-001\", version=1, plan_status=\"draft\")\n"
        "        mock_repos[\"plan_repo\"].get_current_by_plan_id.return_value = self._plan_model\n",
        "        self._plan_model = _make_plan_model(plan_id=\"plan-001\", version=1, plan_status=\"draft\")\n"
        "        self._plan_model.summary = \"Validated treatment plan\"\n"
        "        self._plan_model.clinical_rationale = \"Evidence-supported rationale\"\n"
        "        medication = MagicMock()\n"
        "        medication.item_id = \"item-001\"\n"
        "        medication.item_type = \"medication\"\n"
        "        medication.planned_dose_text = \"20 mg\"\n"
        "        medication.route = \"oral\"\n"
        "        medication.frequency = \"once daily\"\n"
        "        monitoring = MagicMock()\n"
        "        monitoring.monitoring_id = \"monitoring-001\"\n"
        "        monitoring.schedule = \"baseline and every 4 weeks\"\n"
        "        monitoring.action_if_abnormal = \"Hold and reassess\"\n"
        "        self._plan_model.items = [medication]\n"
        "        self._plan_model.monitoring = [monitoring]\n"
        "        self._plan_model.safety_rules = []\n"
        "        self._plan_model.approved_by = USER_UUID\n"
        "        self._plan_model.approved_at = datetime.now(timezone.utc).replace(tzinfo=None)\n"
        "        mock_repos[\"plan_repo\"].get_current_by_plan_id.return_value = self._plan_model\n",
    )


if __name__ == "__main__":
    main()
