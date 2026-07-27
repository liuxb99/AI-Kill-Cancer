"""Phase 3D — Clinical Graph Event Schema Tests."""


import pytest

from src.backend.schemas.clinical_graph_event import (
    SENSITIVE_FIELDS,
    ClinicalGraphEvent,
    GraphAggregateType,
    GraphEventType,
)


class TestClinicalGraphEventSchema:
    """Event Schema 序列化与验证测试。"""

    def test_serialization(self):
        """基本序列化/反序列化。"""
        event = ClinicalGraphEvent(
            event_type=GraphEventType.PATIENT_CREATED,
            aggregate_type=GraphAggregateType.PATIENT,
            aggregate_id="patient-123",
            payload={"patient_id": "patient-123", "display_name": "ANON"},
        )
        assert event.event_id is not None
        assert event.schema_version == 1
        assert event.event_type == GraphEventType.PATIENT_CREATED

    def test_schema_version_default(self):
        """schema_version 默认值为 1。"""
        event = ClinicalGraphEvent(
            event_type=GraphEventType.RECOMMENDATION_CREATED,
            aggregate_type=GraphAggregateType.RECOMMENDATION,
            aggregate_id="rec-1",
        )
        assert event.schema_version == 1

    def test_sensitive_field_exclusion(self):
        """验证敏感字段检测。"""
        event = ClinicalGraphEvent(
            event_type=GraphEventType.PATIENT_CREATED,
            aggregate_type=GraphAggregateType.PATIENT,
            aggregate_id="p-1",
            payload={"patient_id": "p-1", "password_hash": "should_not_exist"},
        )
        assert not event.validate_payload_sensitive_fields()

    def test_clean_payload_passes_sensitive_check(self):
        """干净的 payload 通过敏感字段检查。"""
        event = ClinicalGraphEvent(
            event_type=GraphEventType.PATIENT_CREATED,
            aggregate_type=GraphAggregateType.PATIENT,
            aggregate_id="p-1",
            payload={"patient_id": "p-1", "display_name": "Test"},
        )
        assert event.validate_payload_sensitive_fields()

    def test_invalid_event_type_rejected(self):
        """无效的 event_type 被 Pydantic 拒绝。"""
        with pytest.raises(ValueError):
            ClinicalGraphEvent(
                event_type="invalid.type",  # type: ignore
                aggregate_type=GraphAggregateType.PATIENT,
                aggregate_id="p-1",
            )

    def test_all_event_types_have_create(self):
        """所有支持的 event_type 都有 create 变体。"""
        create_events = [
            GraphEventType.PATIENT_CREATED,
            GraphEventType.RECOMMENDATION_CREATED,
            GraphEventType.CLINICAL_DECISION_CREATED,
            GraphEventType.TUMOR_BOARD_CONSENSUS_CREATED,
        ]
        for evt in create_events:
            assert evt.value.endswith(".created")

    def test_all_event_types_have_update(self):
        """所有支持的 event_type 都有 update 变体。"""
        update_events = [
            GraphEventType.PATIENT_UPDATED,
            GraphEventType.RECOMMENDATION_UPDATED,
            GraphEventType.CLINICAL_DECISION_UPDATED,
            GraphEventType.TUMOR_BOARD_CONSENSUS_UPDATED,
        ]
        for evt in update_events:
            assert evt.value.endswith(".updated")

    def test_sensitive_fields_set(self):
        """SENSITIVE_FIELDS 包含预期字段。"""
        assert "password_hash" in SENSITIVE_FIELDS
        assert "token" in SENSITIVE_FIELDS
        assert "database_url" in SENSITIVE_FIELDS

    def test_serialize_to_dict(self):
        """Event 可序列化为 dict。"""
        event = ClinicalGraphEvent(
            event_type=GraphEventType.PATIENT_CREATED,
            aggregate_type=GraphAggregateType.PATIENT,
            aggregate_id="p-1",
            payload={"patient_id": "p-1"},
        )
        d = event.model_dump()
        assert d["event_type"] == "patient.created"
        assert d["schema_version"] == 1
        assert d["aggregate_id"] == "p-1"
