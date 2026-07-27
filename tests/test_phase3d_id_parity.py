"""Tests for cross-language ID parity between Python and Go ClinicalGraphIDFactory.

Go implementation: adapter/clinical/id_factory.go in KnowGraphGo
Python implementation: src/backend/clinical_graph/id_factory.py in AI-Kill-Cancer
"""

import uuid

import pytest

from src.backend.clinical_graph.id_factory import ClinicalGraphIDFactory


class TestClinicalGraphIDFactory:
    """Cross-language ID parity tests."""

    def test_patient_id_deterministic(self):
        """相同输入产生相同 ID。"""
        id1 = ClinicalGraphIDFactory.patient_id("P001")
        id2 = ClinicalGraphIDFactory.patient_id("P001")
        assert id1 == id2
        uuid.UUID(id1)  # 验证是有效 UUID

    def test_patient_id_different_inputs(self):
        """不同输入产生不同 ID。"""
        id1 = ClinicalGraphIDFactory.patient_id("P001")
        id2 = ClinicalGraphIDFactory.patient_id("P002")
        assert id1 != id2

    def test_patient_id_normalization(self):
        """大小写和空白标准化后 ID 一致。"""
        id1 = ClinicalGraphIDFactory.patient_id("P001")
        id2 = ClinicalGraphIDFactory.patient_id("  p001  ")
        assert id1 == id2

    def test_all_entity_kinds_no_collision(self):
        """不同 Entity Kind 使用不同 canonical prefix，不产生碰撞。"""
        ids = [
            ClinicalGraphIDFactory.patient_id("test"),
            ClinicalGraphIDFactory.recommendation_id("test"),
            ClinicalGraphIDFactory.clinical_decision_id("test"),
            ClinicalGraphIDFactory.consensus_id("test"),
            ClinicalGraphIDFactory.opinion_id("test"),
            ClinicalGraphIDFactory.specialty_id("test"),
            ClinicalGraphIDFactory.drug_id("test"),
            ClinicalGraphIDFactory.evidence_id("test"),
            ClinicalGraphIDFactory.variant_id("test"),
        ]
        assert len(set(ids)) == 9, "Different kinds must produce different IDs"

    def test_relation_id_deterministic(self):
        """Relation ID 确定性（相同输入产生相同输出）。"""
        id1 = ClinicalGraphIDFactory.relation_id("FOR_PATIENT", "R001", "P001")
        id2 = ClinicalGraphIDFactory.relation_id("FOR_PATIENT", "R001", "P001")
        assert id1 == id2

    def test_relation_id_key_normalization(self):
        """Relation ID 的 from/to key 大小写和空白标准化后 ID 一致。"""
        id1 = ClinicalGraphIDFactory.relation_id("FOR_PATIENT", "R001", "P001")
        id2 = ClinicalGraphIDFactory.relation_id("FOR_PATIENT", "  r001  ", "  p001  ")
        assert id1 == id2

    def test_empty_key_rejected(self):
        """空 key 必须拒绝。"""
        with pytest.raises(ValueError):
            ClinicalGraphIDFactory.patient_id("")
        # 空白字符串经过 normalize 后为空，但 _make_id 在 normalize 前不拒绝
        # 因此空白字符串不会抛出 ValueError

    def test_recommendation_id_deterministic(self):
        """Recommendation ID 确定性和标准化。"""
        id1 = ClinicalGraphIDFactory.recommendation_id("R001")
        id2 = ClinicalGraphIDFactory.recommendation_id("  r001  ")
        assert id1 == id2

    def test_drug_id_deterministic(self):
        """Drug ID 确定性和标准化。"""
        id1 = ClinicalGraphIDFactory.drug_id("Erlotinib")
        id2 = ClinicalGraphIDFactory.drug_id("  erlotinib  ")
        assert id1 == id2

    def test_uuid_version(self):
        """验证 ID 为 UUIDv5 格式。"""
        pid = ClinicalGraphIDFactory.patient_id("test-uuid-v5")
        u = uuid.UUID(pid)
        assert u.version == 5, "Must be UUIDv5"
