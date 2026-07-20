"""
Domain enums for AI-Kill-Cancer Precision Oncology platform.

All enum values are stable identifiers — do not change them after deploying
a migration that references them in the database.
"""

from __future__ import annotations

import enum


class SexEnum(str, enum.Enum):
    M = "M"
    F = "F"
    UNKNOWN = "unknown"


class ConsentStatusEnum(str, enum.Enum):
    GRANTED = "granted"
    REVOKED = "revoked"
    EXPIRED = "expired"
    PENDING = "pending"


class CancerTypeEnum(str, enum.Enum):
    """Thyroid cancer types supported in MVP."""
    PTC = "PTC"                      # Papillary thyroid carcinoma
    FTC = "FTC"                      # Follicular thyroid carcinoma
    MTC = "MTC"                      # Medullary thyroid carcinoma
    HCC = "HCC"                      # Hürthle cell carcinoma
    PDTC = "PDTC"                    # Poorly differentiated thyroid carcinoma
    ATC = "ATC"                      # Anaplastic thyroid carcinoma


class SpecimenTypeEnum(str, enum.Enum):
    FFPE = "FFPE"
    FRESH_FROZEN = "fresh_frozen"
    BLOOD = "blood"
    BONE_MARROW = "bone_marrow"
    FNA = "FNA"
    OTHER = "other"


class VariantTypeEnum(str, enum.Enum):
    SNV = "SNV"
    INDEL = "indel"
    CNV_AMPLIFICATION = "copy-number_amplification"
    CNV_DELETION = "copy-number_deletion"
    FUSION = "fusion"
    STRUCTURAL_VARIANT = "structural_variant"
    TERT_PROMOTER = "TERT_promoter"
    MSI_TMB = "MSI_TMB"


class VariantOriginEnum(str, enum.Enum):
    SOMATIC = "somatic"
    GERMLINE = "germline"
    UNKNOWN = "unknown"


class OncogenicityEnum(str, enum.Enum):
    ONCOGENIC = "oncogenic"
    LIKELY_ONCOGENIC = "likely_oncogenic"
    VUS = "VUS"
    LIKELY_BENIGN = "likely_benign"
    BENIGN = "benign"
    NOT_ASSESSED = "not_assessed"


class DriverStatusEnum(str, enum.Enum):
    DRIVER = "driver"
    LIKELY_DRIVER = "likely_driver"
    PASSENGER = "passenger"
    UNKNOWN = "unknown"


class ZygosityEnum(str, enum.Enum):
    HETEROZYGOUS = "heterozygous"
    HOMOZYGOUS = "homozygous"
    HEMIZYGOUS = "hemizygous"
    UNKNOWN = "unknown"


class NormalizationStatusEnum(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"


class EvidenceDirectionEnum(str, enum.Enum):
    SUPPORTING = "supporting"
    CONFLICTING = "conflicting"
    NEUTRAL = "neutral"
    INSUFFICIENT = "insufficient"


class EvidenceLevelEnum(str, enum.Enum):
    LEVEL_1 = "Level_1"   # Same cancer, same molecular — regulatory approval
    LEVEL_2 = "Level_2"   # Same cancer, same molecular — clinical trial
    LEVEL_3 = "Level_3"   # Other cancer, same molecular — human evidence
    LEVEL_4 = "Level_4"   # Preclinical
    LEVEL_5 = "Level_5"   # Computational / network hypothesis
    NOT_ASSESSED = "not_assessed"


class EvidenceTypeEnum(str, enum.Enum):
    PREDICTIVE = "predictive"
    PROGNOSTIC = "prognostic"
    DIAGNOSTIC = "diagnostic"
    MECHANISM = "mechanism"
    SAFETY = "safety"
    OTHER = "other"


class CandidateCategoryEnum(str, enum.Enum):
    APPROVED_SAME_CONTEXT = "approved_for_same_context"
    APPROVED_OTHER_CANCER = "approved_for_other_cancer"
    CLINICAL_TRIAL = "clinical_trial"
    PRECLINICAL = "preclinical"
    REPURPOSING_HYPOTHESIS = "repurposing_hypothesis"


class AnalysisStatusEnum(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    NOT_CONFIGURED = "not_configured"


class UploadStatusEnum(str, enum.Enum):
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    FAILED = "failed"
    DELETED = "deleted"


class ValidationStatusEnum(str, enum.Enum):
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    NOT_APPLICABLE = "not_applicable"


class FileTypeEnum(str, enum.Enum):
    VCF = "VCF"
    VCF_GZ = "VCF.GZ"
    CSV = "CSV"
    TSV = "TSV"
    JSON = "JSON"
    PDF = "PDF"


class AnalysisModeEnum(str, enum.Enum):
    DEMO = "demo"
    RESEARCH = "research"
    PRODUCTION = "production"


class AnalysisResultTypeEnum(str, enum.Enum):
    SOMATIC = "somatic"
    GERMLINE = "germline"
    RNA = "RNA"
    PROTEIN = "protein"


class ConsentTypeEnum(str, enum.Enum):
    RESEARCH = "research"
    CLINICAL = "clinical"
    DATA_SHARING = "data_sharing"
    GERMLINE_ANALYSIS = "germline_analysis"


class AuditActionEnum(str, enum.Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    SHARE = "share"
    CONSENT_GRANT = "consent_grant"
    CONSENT_REVOKE = "consent_revoke"
    ANALYSIS_START = "analysis_start"
    ANALYSIS_COMPLETE = "analysis_complete"
