"""Tests for full rebuild idempotency of Clinical Graph Event schema.

These tests verify that events can be serialized and deserialized
without loss, which is a prerequisite for event-sourced rebuild.
"""

from src.backend.schemas.clinical_graph_event import (
    ClinicalGraphEvent,
    GraphEventType,
    GraphAggregateType,
)


class TestRebuildEventSchema:
    """Event schema serialization round-trip tests."""

    def test_event_schema_roundtrip(self):
        """Event schema serialization round-trip preserves all fields."""
        event = ClinicalGraphEvent(
            event_id="test-eid-001",
            event_type=GraphEventType.PATIENT_CREATED,
            schema_version=1,
            aggregate_type=GraphAggregateType.PATIENT,
            aggregate_id="P001",
            payload={"patient_id": "P001", "display_name": "Test Patient"},
        )
        data = event.model_dump()
        restored = ClinicalGraphEvent(**data)

        assert restored.event_id == event.event_id
        assert restored.event_type == event.event_type
        assert restored.schema_version == event.schema_version
        assert restored.aggregate_type == event.aggregate_type
        assert restored.aggregate_id == event.aggregate_id
        assert restored.payload == event.payload
        assert restored.actor_id == event.actor_id
        assert restored.correlation_id == event.correlation_id

    def test_event_roundtrip_all_event_types(self):
        """所有事件类型 round-trip 均正常。"""
        for event_type in GraphEventType:
            for agg_type in GraphAggregateType:
                event = ClinicalGraphEvent(
                    event_id=f"test-{event_type.value}-{agg_type.value}",
                    event_type=event_type,
                    schema_version=1,
                    aggregate_type=agg_type,
                    aggregate_id="test-id",
                    payload={"key": "value"},
                )
                data = event.model_dump()
                restored = ClinicalGraphEvent(**data)
                assert restored.event_type == event_type
                assert restored.aggregate_type == agg_type

    def test_event_schema_version_minimum(self):
        """schema_version 默认值为 1。"""
        event = ClinicalGraphEvent(
            event_type=GraphEventType.PATIENT_CREATED,
            aggregate_type=GraphAggregateType.PATIENT,
            aggregate_id="P001",
        )
        assert event.schema_version >= 1

    def test_payload_sensitive_fields_detection(self):
        """敏感字段检测功能正常。"""
        event = ClinicalGraphEvent(
            event_type=GraphEventType.RECOMMENDATION_CREATED,
            aggregate_type=GraphAggregateType.RECOMMENDATION,
            aggregate_id="R001",
            payload={"drug_name": "Erlotinib", "password_hash": "xxx"},
        )
        assert not event.validate_payload_sensitive_fields()

    def test_payload_no_sensitive_fields(self):
        """无敏感字段时检测通过。"""
        event = ClinicalGraphEvent(
            event_type=GraphEventType.RECOMMENDATION_CREATED,
            aggregate_type=GraphAggregateType.RECOMMENDATION,
            aggregate_id="R001",
            payload={"drug_name": "Erlotinib", "evidence_score": 0.85},
        )
        assert event.validate_payload_sensitive_fields()

    def test_event_id_uniqueness(self):
        """默认 event_id 为随机 UUID，两次构造不同。"""
        e1 = ClinicalGraphEvent(
            event_type=GraphEventType.PATIENT_CREATED,
            aggregate_type=GraphAggregateType.PATIENT,
            aggregate_id="P001",
        )
        e2 = ClinicalGraphEvent(
            event_type=GraphEventType.PATIENT_CREATED,
            aggregate_type=GraphAggregateType.PATIENT,
            aggregate_id="P001",
        )
        assert e1.event_id != e2.event_id
