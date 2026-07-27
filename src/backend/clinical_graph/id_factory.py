"""ClinicalGraphIDFactory — 确定性 UUIDv5 实体/关系 ID 生成器。

与 KnowGraphGo (Go) 的 ClinicalIDFactory 完全一致：
- 使用相同的 CLINICAL_NAMESPACE (UUIDv5)
- 使用相同的 canonical key 格式
- 使用相同的规范化规则 (trim + lowercase)
- 生成的 ID 跨语言可互换
"""

import uuid

# Go 版 ClinicalNamespace: a7b4e5c2-8d9f-4a3b-8c1d-6e9f2a7b3c5d
CLINICAL_NAMESPACE = uuid.UUID("a7b4e5c2-8d9f-4a3b-8c1d-6e9f2a7b3c5d")


class ClinicalGraphIDFactory:
    """临床知识图谱确定性 ID 工厂。

    所有方法均为静态方法，返回 UUIDv5 字符串。
    相同输入保证相同输出，适用于事件溯源重播。
    """

    @staticmethod
    def patient_id(patient_id: str) -> str:
        """生成 patient 实体的确定性 UUID。"""
        return _make_id("clinical:patient:", patient_id)

    @staticmethod
    def recommendation_id(rid: str) -> str:
        """生成 recommendation 实体的确定性 UUID。"""
        return _make_id("clinical:recommendation:", rid)

    @staticmethod
    def clinical_decision_id(did: str) -> str:
        """生成 clinical_decision 实体的确定性 UUID。"""
        return _make_id("clinical:decision:", did)

    @staticmethod
    def consensus_id(cid: str) -> str:
        """生成 tumor_board_consensus 实体的确定性 UUID。"""
        return _make_id("clinical:consensus:", cid)

    @staticmethod
    def opinion_id(oid: str) -> str:
        """生成 specialist_opinion 实体的确定性 UUID。"""
        return _make_id("clinical:opinion:", oid)

    @staticmethod
    def specialty_id(s: str) -> str:
        """生成 specialty 实体的确定性 UUID。"""
        return _make_id("clinical:specialty:", s)

    @staticmethod
    def drug_id(did: str) -> str:
        """生成 drug 实体的确定性 UUID。"""
        return _make_id("clinical:drug:", did)

    @staticmethod
    def evidence_id(eid: str) -> str:
        """生成 evidence 实体的确定性 UUID。"""
        return _make_id("clinical:evidence:", eid)

    @staticmethod
    def variant_id(vid: str) -> str:
        """生成 variant 实体的确定性 UUID。"""
        return _make_id("clinical:variant:", vid)

    @staticmethod
    def relation_id(kind: str, from_key: str, to_key: str) -> str:
        """生成关系的确定性 UUID。

        canonical key 格式:
            clinical:relation:{kind}:{normalized_from}:{normalized_to}
        """
        canonical = f"clinical:relation:{kind}:{_normalize(from_key)}:{_normalize(to_key)}"
        return str(uuid.uuid5(CLINICAL_NAMESPACE, canonical))


def _normalize(s: str) -> str:
    """规范化：去除首尾空白并转为小写。"""
    return s.strip().lower()


def _make_id(prefix: str, key: str) -> str:
    """内部 ID 生成函数。

    canonical key = prefix + normalized_key
    例如 "clinical:patient:" + "abc123" → "clinical:patient:abc123"
    """
    if not key:
        raise ValueError(f"Empty key for prefix {prefix!r}")
    return str(uuid.uuid5(CLINICAL_NAMESPACE, prefix + _normalize(key)))


__all__ = ["ClinicalGraphIDFactory", "CLINICAL_NAMESPACE"]
