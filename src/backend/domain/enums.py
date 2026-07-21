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
    PARTIAL = "partial"
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


class ConsequenceEnum(str, enum.Enum):
    """Sequence Ontology (SO) consequence terms for variant annotation."""
    MISSENSE_VARIANT = "missense_variant"
    NONSENSE_VARIANT = "nonsense_variant"
    SYNONYMOUS_VARIANT = "synonymous_variant"
    FRAMESHIFT_VARIANT = "frameshift_variant"
    STOP_GAINED = "stop_gained"
    STOP_LOST = "stop_lost"
    START_LOST = "start_lost"
    SPLICE_ACCEPTOR = "splice_acceptor"
    SPLICE_DONOR = "splice_donor"
    SPLICE_REGION = "splice_region"
    INFRAME_INSERTION = "inframe_insertion"
    INFRAME_DELETION = "inframe_deletion"
    PROTEIN_ALTERING = "protein_altering"
    INTRON_VARIANT = "intron_variant"
    UPSTREAM_GENE = "upstream_gene"
    DOWNSTREAM_GENE = "downstream_gene"
    UTR_VARIANT = "UTR_variant"
    NON_CODING_TRANSCRIPT = "non_coding_transcript"
    INTERGENIC_VARIANT = "intergenic_variant"
    REGULATORY_REGION = "regulatory_region"
    TF_BINDING_SITE = "TF_binding_site"
    FEATURE_ELONGATION = "feature_elongation"
    FEATURE_TRUNCATION = "feature_truncation"
    CODING_SEQUENCE = "coding_sequence"
    MATURE_MIRNA = "mature_miRNA"
    NMD_TRANSCRIPT = "NMD_transcript"
    NO_CONSEQUENCE = "no_consequence"
    OTHER = "other"


class VCFStatusEnum(str, enum.Enum):
    """Status of VCF file processing."""
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    VALID = "valid"
    INVALID = "invalid"
    NORMALIZING = "normalizing"
    NORMALIZED = "normalized"
    ANNOTATING = "annotating"
    ANNOTATED = "annotated"
    FAILED = "failed"


class NormalizationMethodEnum(str, enum.Enum):
    """Method used for variant normalization."""
    NOT_APPLICABLE = "not_applicable"
    MINIMAL_REPRESENTATION = "minimal_representation"
    BCFTOOLS_CANONICAL = "bcftools_canonical"


class NormalizationResultEnum(str, enum.Enum):
    """Overall result of variant normalization."""
    NOT_ATTEMPTED = "not_attempted"
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"
    REFERENCE_UNAVAILABLE = "reference_unavailable"


class NormalizationSemanticsEnum(str, enum.Enum):
    """What the normalization operation actually achieved."""
    MINIMAL_REPRESENTATION_ONLY = "minimal_representation_only"
    CANONICAL_WITH_REFERENCE = "canonical_with_reference"
    NOT_APPLICABLE = "not_applicable"


class GenomeBuildConfidenceEnum(str, enum.Enum):
    """Confidence level of genome build detection."""
    EXPLICIT = "explicit"  # User-specified or sequencing test metadata
    HEADER_CONFIRMED = "header_confirmed"  # VCF header matches explicit
    HEADER_DETECTED = "header_detected"  # Only VCF header
    CONTENT_DETECTED = "content_detected"  # Guessed from content
    CONFLICT = "conflict"  # Multiple sources disagree
    UNKNOWN = "unknown"


class UploadDuplicateStrategyEnum(str, enum.Enum):
    """Strategy for handling duplicate uploads."""
    REJECT = "reject"
    ACCEPT_NEW = "accept_new"
    DEDUPLICATE_RETURN_EXISTING = "deduplicate_return_existing"


class UploadEligibilityEnum(str, enum.Enum):
    """Whether the upload is eligible for analysis."""
    ELIGIBLE = "eligible"
    INVALID = "invalid"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"
    PENDING_VALIDATION = "pending_validation"


class ConsentTypeEnum(str, enum.Enum):
    RESEARCH = "research"
    CLINICAL = "clinical"
    DATA_SHARING = "data_sharing"
    GERMLINE_ANALYSIS = "germline_analysis"


class AuditActionEnum(str, enum.Enum):
    CREATE = "create"


# ── Auth enums (imported by domain/user.py and auth/models.py) ──────────

class Role(str, enum.Enum):
    ADMIN = "admin"
    CLINICIAN = "clinician"
    RESEARCHER = "researcher"
    REVIEWER = "reviewer"
    VIEWER = "viewer"
    SERVICE = "service"


class Permission(str, enum.Enum):
    # Patient/Case permissions
    READ_PATIENT = "read:patient"
    WRITE_PATIENT = "write:patient"
    DELETE_PATIENT = "delete:patient"
    # Evidence permissions
    READ_EVIDENCE = "read:evidence"
    REFRESH_EVIDENCE = "refresh:evidence"
    # Ranking permissions
    READ_RANKING = "read:ranking"
    RUN_RANKING = "run:ranking"
    # Reasoning permissions
    READ_REASONING = "read:reasoning"
    RUN_REASONING = "run:reasoning"
    # Report permissions
    READ_REPORT = "read:report"
    CREATE_REPORT = "create:report"
    DOWNLOAD_REPORT = "download:report"
    # Admin permissions
    MANAGE_USERS = "manage:users"
    MANAGE_SETTINGS = "manage:settings"
    VIEW_AUDIT = "view:audit"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    SHARE = "share"
    CONSENT_GRANT = "consent_grant"
    CONSENT_REVOKE = "consent_revoke"
    ANALYSIS_START = "analysis_start"
    ANALYSIS_COMPLETE = "analysis_complete"
