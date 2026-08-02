"""Phase 3F-1 treatment graph ID contract tests."""

import uuid

import pytest

from src.backend.clinical_graph.id_factory import (
    CLINICAL_NAMESPACE,
    ClinicalGraphIDFactory,
)


ENTITY_CASES = {
    "treatment_plan": ClinicalGraphIDFactory.treatment_plan_id,
    "treatment_phase": ClinicalGraphIDFactory.treatment_phase_id,
    "treatment_item": ClinicalGraphIDFactory.treatment_item_id,
    "monitoring": ClinicalGraphIDFactory.monitoring_id,
    "safety_rule": ClinicalGraphIDFactory.safety_rule_id,
}


@pytest.mark.parametrize(("kind", "factory"), ENTITY_CASES.items())
def test_treatment_entity_ids_follow_canonical_uuid5_contract(kind, factory):
    business_key = "  PLAN-001  "
    expected = str(
        uuid.uuid5(
            CLINICAL_NAMESPACE,
            f"clinical:{kind}:plan-001",
        )
    )

    assert factory(business_key) == expected
    assert factory("plan-001") == expected
    assert uuid.UUID(expected).version == 5


def test_treatment_entity_kinds_do_not_collide():
    generated = {factory("shared-key") for factory in ENTITY_CASES.values()}
    assert len(generated) == len(ENTITY_CASES)


@pytest.mark.parametrize("factory", ENTITY_CASES.values())
@pytest.mark.parametrize("invalid", ["", "   ", "\t\n"])
def test_treatment_entity_factories_reject_blank_keys(factory, invalid):
    with pytest.raises(ValueError):
        factory(invalid)


@pytest.mark.parametrize("invalid", ["", "   ", "\t"])
def test_relation_factory_rejects_blank_components(invalid):
    with pytest.raises(ValueError):
        ClinicalGraphIDFactory.relation_id(invalid, "from", "to")
    with pytest.raises(ValueError):
        ClinicalGraphIDFactory.relation_id("kind", invalid, "to")
    with pytest.raises(ValueError):
        ClinicalGraphIDFactory.relation_id("kind", "from", invalid)


def test_non_string_keys_fail_explicitly():
    with pytest.raises(TypeError):
        ClinicalGraphIDFactory.treatment_plan_id(None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        ClinicalGraphIDFactory.relation_id("kind", 1, "to")  # type: ignore[arg-type]
