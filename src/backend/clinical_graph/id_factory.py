"""ClinicalGraphIDFactory — 確定性 UUIDv5 實體／關係 ID 產生器。

與 KnowGraphGo 的 ClinicalIDFactory 使用同一組 namespace、canonical key
與正規化規則，確保事件重播及跨語言查詢可得到完全一致的圖譜 ID。
"""

import uuid

CLINICAL_NAMESPACE = uuid.UUID("a7b4e5c2-8d9f-4a3b-8c1d-6e9f2a7b3c5d")


class ClinicalGraphIDFactory:
    """臨床知識圖譜確定性 ID 工廠。"""

    @staticmethod
    def patient_id(patient_id: str) -> str:
        return _make_id("clinical:patient:", patient_id)

    @staticmethod
    def recommendation_id(rid: str) -> str:
        return _make_id("clinical:recommendation:", rid)

    @staticmethod
    def clinical_decision_id(did: str) -> str:
        return _make_id("clinical:decision:", did)

    @staticmethod
    def consensus_id(cid: str) -> str:
        return _make_id("clinical:consensus:", cid)

    @staticmethod
    def opinion_id(oid: str) -> str:
        return _make_id("clinical:opinion:", oid)

    @staticmethod
    def specialty_id(specialty: str) -> str:
        return _make_id("clinical:specialty:", specialty)

    @staticmethod
    def drug_id(did: str) -> str:
        return _make_id("clinical:drug:", did)

    @staticmethod
    def evidence_id(eid: str) -> str:
        return _make_id("clinical:evidence:", eid)

    @staticmethod
    def variant_id(vid: str) -> str:
        return _make_id("clinical:variant:", vid)

    @staticmethod
    def treatment_plan_id(plan_id: str) -> str:
        """產生 treatment_plan 實體 ID。"""
        return _make_id("clinical:treatment_plan:", plan_id)

    @staticmethod
    def treatment_phase_id(phase_id: str) -> str:
        """產生 treatment_phase 實體 ID。"""
        return _make_id("clinical:treatment_phase:", phase_id)

    @staticmethod
    def treatment_item_id(item_id: str) -> str:
        """產生 treatment_item 實體 ID。"""
        return _make_id("clinical:treatment_item:", item_id)

    @staticmethod
    def monitoring_id(monitoring_id: str) -> str:
        """產生 monitoring 實體 ID。"""
        return _make_id("clinical:monitoring:", monitoring_id)

    @staticmethod
    def safety_rule_id(rule_id: str) -> str:
        """產生 safety_rule 實體 ID。"""
        return _make_id("clinical:safety_rule:", rule_id)

    @staticmethod
    def relation_id(kind: str, from_key: str, to_key: str) -> str:
        normalized_kind = _require_key(kind, "clinical:relation:kind:")
        normalized_from = _require_key(from_key, "clinical:relation:from:")
        normalized_to = _require_key(to_key, "clinical:relation:to:")
        canonical = (
            f"clinical:relation:{normalized_kind}:"
            f"{normalized_from}:{normalized_to}"
        )
        return str(uuid.uuid5(CLINICAL_NAMESPACE, canonical))


def _normalize(value: str) -> str:
    return value.strip().lower()


def _require_key(value: str, prefix: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"Key for prefix {prefix!r} must be a string")
    normalized = _normalize(value)
    if not normalized:
        raise ValueError(f"Empty key for prefix {prefix!r}")
    return normalized


def _make_id(prefix: str, key: str) -> str:
    return str(uuid.uuid5(CLINICAL_NAMESPACE, prefix + _require_key(key, prefix)))


__all__ = ["ClinicalGraphIDFactory", "CLINICAL_NAMESPACE"]
