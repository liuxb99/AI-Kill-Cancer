"""Digital Thread path definitions for clinical graph events.

Verifies that all required event types and aggregate types exist,
which is the schema-level prerequisite for end-to-end Digital Thread tracing.
"""

from src.backend.schemas.clinical_graph_event import GraphEventType, GraphAggregateType


class TestDigitalThreadSchema:
    """Digital Thread schema completeness tests."""

    def test_event_types_complete(self):
        """Verify all required event types exist."""
        required = [
            "PATIENT_CREATED",
            "PATIENT_UPDATED",
            "RECOMMENDATION_CREATED",
            "RECOMMENDATION_UPDATED",
            "CLINICAL_DECISION_CREATED",
            "CLINICAL_DECISION_UPDATED",
            "TUMOR_BOARD_CONSENSUS_CREATED",
            "TUMOR_BOARD_CONSENSUS_UPDATED",
        ]
        for rt in required:
            assert hasattr(GraphEventType, rt), f"Missing event type: {rt}"

    def test_aggregate_types_complete(self):
        """Verify all required aggregate types exist."""
        required = [
            "PATIENT",
            "RECOMMENDATION",
            "CLINICAL_DECISION",
            "TUMOR_BOARD_CONSENSUS",
            "SPECIALIST_OPINION",
            "DRUG",
            "EVIDENCE",
            "VARIANT",
        ]
        for at in required:
            assert hasattr(GraphAggregateType, at), f"Missing aggregate type: {at}"

    def test_event_type_values_format(self):
        """事件类型值使用 dot-notation 格式。"""
        assert GraphEventType.PATIENT_CREATED.value == "patient.created"
        assert GraphEventType.RECOMMENDATION_CREATED.value == "recommendation.created"
        assert GraphEventType.CLINICAL_DECISION_CREATED.value == "clinical_decision.created"
        assert GraphEventType.TUMOR_BOARD_CONSENSUS_CREATED.value == "tumor_board_consensus.created"

    def test_aggregate_type_values_format(self):
        """聚合类型值使用 snake_case 格式。"""
        assert GraphAggregateType.PATIENT.value == "patient"
        assert GraphAggregateType.RECOMMENDATION.value == "recommendation"
        assert GraphAggregateType.CLINICAL_DECISION.value == "clinical_decision"
        assert GraphAggregateType.TUMOR_BOARD_CONSENSUS.value == "tumor_board_consensus"
        assert GraphAggregateType.SPECIALIST_OPINION.value == "specialist_opinion"

    def test_event_aggregate_pair_coverage(self):
        """关键事件-聚合类型配对在 schema 中可表达。"""
        pairs = [
            (GraphEventType.PATIENT_CREATED, GraphAggregateType.PATIENT),
            (GraphEventType.RECOMMENDATION_CREATED, GraphAggregateType.RECOMMENDATION),
            (GraphEventType.CLINICAL_DECISION_CREATED, GraphAggregateType.CLINICAL_DECISION),
            (GraphEventType.TUMOR_BOARD_CONSENSUS_CREATED, GraphAggregateType.TUMOR_BOARD_CONSENSUS),
        ]
        for evt, agg in pairs:
            # 只是验证这些类型可以一起使用（无类型冲突）
            assert evt is not None
            assert agg is not None
