"""Tests for cross-language ID parity between Python and Go ClinicalGraphIDFactory.

Go implementation: adapter/clinical/id_factory.go in KnowGraphGo
Python implementation: src/backend/clinical_graph/id_factory.py in AI-Kill-Cancer
"""

import json
import os
import subprocess
import uuid
from pathlib import Path

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

    def test_id_parity_with_go_golden(self):
        """与 KnowGraphGo golden_output.json 中的 ID 逐一比对，确保 Python 与 Go 生成一致。"""
        golden_path = Path(__file__).resolve().parents[1] / "KnowGraphGo" / "golden_output.json"
        with open(golden_path) as f:
            cases = json.load(f)

        # 实体 kind → factory 方法映射
        entity_factories = {
            "patient": ClinicalGraphIDFactory.patient_id,
            "recommendation": ClinicalGraphIDFactory.recommendation_id,
            "decision": ClinicalGraphIDFactory.clinical_decision_id,
            "consensus": ClinicalGraphIDFactory.consensus_id,
            "opinion": ClinicalGraphIDFactory.opinion_id,
            "specialty": ClinicalGraphIDFactory.specialty_id,
            "drug": ClinicalGraphIDFactory.drug_id,
            "evidence": ClinicalGraphIDFactory.evidence_id,
            "variant": ClinicalGraphIDFactory.variant_id,
        }

        for case in cases:
            kind = case["kind"]
            bk = case["business_key"]
            expected = case["graph_id"]

            if kind == "relation":
                # business_key 格式: "KIND:FROM:TO"，例如 "FOR_PATIENT:P001:REC-001"
                parts = bk.split(":", maxsplit=2)
                assert len(parts) == 3, f"Invalid relation business_key: {bk}"
                rkind, rfrom, rto = parts
                actual = ClinicalGraphIDFactory.relation_id(rkind, rfrom, rto)
            else:
                factory = entity_factories.get(kind)
                assert factory is not None, f"Unknown kind: {kind}"
                actual = factory(bk)

            assert actual == expected, (
                f"Mismatch for kind={kind!r} key={bk!r}: "
                f"Python got {actual}, Go golden is {expected}"
            )

    def test_id_parity_via_cli(self):
        """直接调用 knowgraph clinical id CLI 验证 Python == Go 输出。"""
        # 寻找 CLI binary
        cli_path = os.path.join(os.path.dirname(__file__), "..", "KnowGraphGo", "knowgraph.exe")
        if not os.path.exists(cli_path):
            cli_path = os.path.join(os.path.dirname(__file__), "..", "KnowGraphGo", "knowgraph")
        if not os.path.exists(cli_path):
            pytest.skip("knowgraph CLI not found")

        test_cases = [
            ("patient", "P001", lambda: ClinicalGraphIDFactory.patient_id("P001")),
            ("recommendation", "REC-001", lambda: ClinicalGraphIDFactory.recommendation_id("REC-001")),
            ("decision", "DC-001", lambda: ClinicalGraphIDFactory.clinical_decision_id("DC-001")),
            ("consensus", "CON-001", lambda: ClinicalGraphIDFactory.consensus_id("CON-001")),
            ("opinion", "OP-001", lambda: ClinicalGraphIDFactory.opinion_id("OP-001")),
            ("specialty", "SP-001", lambda: ClinicalGraphIDFactory.specialty_id("SP-001")),
            ("drug", "DRUG-001", lambda: ClinicalGraphIDFactory.drug_id("DRUG-001")),
            ("evidence", "EV-001", lambda: ClinicalGraphIDFactory.evidence_id("EV-001")),
            ("variant", "VAR-001", lambda: ClinicalGraphIDFactory.variant_id("VAR-001")),
        ]

        for kind, key, py_func in test_cases:
            # CLI output
            result = subprocess.run(
                [cli_path, "clinical", "id", kind, key],
                capture_output=True, text=True, timeout=10,
            )
            assert result.returncode == 0, f"CLI failed for {kind}: {result.stderr}"
            cli_out = json.loads(result.stdout)
            assert cli_out["kind"] == kind
            assert cli_out["business_key"] == key

            # Python output
            py_id = py_func()

            assert cli_out["graph_id"] == py_id, (
                f"Mismatch for kind={kind} key={key}: "
                f"CLI got {cli_out['graph_id']}, Python got {py_id}"
            )

        # Test relation separately
        result = subprocess.run(
            [cli_path, "clinical", "id", "relation", "FOR_PATIENT", "P001", "REC-001"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0, f"CLI failed for relation: {result.stderr}"
        cli_rel = json.loads(result.stdout)
        assert cli_rel["kind"] == "relation"
        py_rel_id = ClinicalGraphIDFactory.relation_id("FOR_PATIENT", "P001", "REC-001")
        assert cli_rel["graph_id"] == py_rel_id, (
            f"Mismatch for relation: CLI got {cli_rel['graph_id']}, Python got {py_rel_id}"
        )
