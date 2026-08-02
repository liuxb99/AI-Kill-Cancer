"""Architecture guards for Phase 3G clinical safety closure."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "src/backend/services/treatment_plan_service.py"
GATE = ROOT / "src/backend/clinical/treatment_plan_safety_gate.py"


def _tree(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_safety_gate_is_framework_independent():
    imports: list[str] = []
    for node in ast.walk(_tree(GATE)):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)

    forbidden = ("fastapi", "pydantic", "sqlalchemy", "src.backend.api")
    assert not [name for name in imports if name.startswith(forbidden)]


def test_treatment_plan_service_owns_safety_gate():
    text = SERVICE.read_text(encoding="utf-8")
    assert "TreatmentPlanSafetyGate" in text
    assert "self._safety_gate = TreatmentPlanSafetyGate()" in text
    assert "async def get_safety_gate(" in text


def test_approval_and_activation_execute_gate_before_mutation():
    text = SERVICE.read_text(encoding="utf-8")
    gate_call = "self._safety_gate.assert_can_transition(model, target_status.value)"
    mutation = "model.plan_status = target_status.value"
    assert gate_call in text
    assert text.index(gate_call) < text.index(mutation)


def test_gate_error_remains_a_value_error_for_existing_api_mapping():
    from src.backend.clinical.treatment_plan_safety_gate import ClinicalSafetyGateError

    assert issubclass(ClinicalSafetyGateError, ValueError)
