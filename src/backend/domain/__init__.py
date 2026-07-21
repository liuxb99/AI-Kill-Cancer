"""
AI-Kill-Cancer Domain Layer

This package contains the core domain models for the Precision Oncology platform.
Each module defines:
- Pydantic schemas for request/response validation
- SQLAlchemy ORM models for persistence
- Enums, constraints, and relationships

Domain models are the single source of truth for data structure.
API routes, repositories, and adapters reference these models.
"""

from src.backend.domain.enums import (
    AnalysisModeEnum,
    AnalysisResultTypeEnum,
    AnalysisStatusEnum,
    AuditActionEnum,
    CandidateCategoryEnum,
    CancerTypeEnum,
    ConsentStatusEnum,
    ConsentTypeEnum,
    DriverStatusEnum,
    EvidenceDirectionEnum,
    EvidenceLevelEnum,
    EvidenceTypeEnum,
    FileTypeEnum,
    NormalizationStatusEnum,
    OncogenicityEnum,
    Permission,
    Role,
    SexEnum,
    SpecimenTypeEnum,
    UploadStatusEnum,
    ValidationStatusEnum,
    VariantOriginEnum,
    VariantTypeEnum,
    ZygosityEnum,
)

from src.backend.domain.patient import (
    PatientModel,
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    PatientListResponse,
)

from src.backend.domain.cancer_case import (
    CancerCaseModel,
    CancerCaseCreate,
    CancerCaseUpdate,
    CancerCaseResponse,
    CancerCaseListResponse,
)

from src.backend.domain.specimen import (
    SpecimenModel,
    SpecimenCreate,
    SpecimenUpdate,
    SpecimenResponse,
)

from src.backend.domain.sequencing_test import (
    SequencingTestModel,
    SequencingTestCreate,
    SequencingTestResponse,
)

from src.backend.domain.uploaded_file import (
    UploadedFileModel,
    UploadedFileCreate,
    UploadedFileResponse,
)

from src.backend.domain.variant import (
    VariantModel,
    VariantImport,
    VariantImportBatch,
    VariantResponse,
    VariantListResponse,
)

from src.backend.domain.gene import (
    GeneModel,
    GeneCreate,
    GeneResponse,
    ProteinModel,
    PathwayModel,
)

from src.backend.domain.drug import (
    DrugModel,
    DrugCreate,
    DrugResponse,
    DrugTargetModel,
)

from src.backend.domain.evidence import (
    EvidenceModel,
    EvidenceCreate,
    EvidenceResponse,
    EvidenceSearchResult,
)

from src.backend.domain.drug_candidate import (
    DrugCandidateModel,
    DrugCandidateResponse,
    DrugCandidateListResponse,
)

from src.backend.domain.publication import PublicationModel

from src.backend.domain.clinical_trial import ClinicalTrialModel

from src.backend.domain.analysis_run import (
    AnalysisRunModel,
    AnalysisRunCreate,
    AnalysisRunResponse,
)

from src.backend.domain.report import ReportModel

from src.backend.domain.consent import (
    ConsentModel,
    ConsentCreate,
    ConsentResponse,
)

from src.backend.domain.audit_log import (
    AuditLogModel,
    AuditLogEntry,
)

from src.backend.domain.visualization_graph import (
    GraphNode,
    GraphEdge,
    VisualizationGraph,
    GraphAnalysisResponse,
    NODE_TYPES,
    EDGE_TYPES,
)

from src.backend.domain.user import (
    UserModel,
    TokenBlacklistModel,
    UserCreate,
    UserResponse,
    TokenResponse,
    LoginRequest,
    RefreshRequest,
    LogoutRequest,
)

from src.backend.domain.case_acl import (
    CaseACLModel,
    CaseRole,
    CASE_ROLE_HIERARCHY,
    CASE_REQUIRED_ROLES,
    CaseACLCreate,
    CaseACLResponse,
    CasePermissionCheck,
)


__all__ = [
    # Enums
    "AnalysisModeEnum",
    "AnalysisResultTypeEnum",
    "AnalysisStatusEnum",
    "AuditActionEnum",
    "CandidateCategoryEnum",
    "CancerTypeEnum",
    "ConsentStatusEnum",
    "ConsentTypeEnum",
    "DriverStatusEnum",
    "EvidenceDirectionEnum",
    "EvidenceLevelEnum",
    "EvidenceTypeEnum",
    "FileTypeEnum",
    "NormalizationStatusEnum",
    "OncogenicityEnum",
    "Permission",
    "Role",
    "SexEnum",
    "SpecimenTypeEnum",
    "UploadStatusEnum",
    "ValidationStatusEnum",
    "VariantOriginEnum",
    "VariantTypeEnum",
    "ZygosityEnum",
    # Models
    "PatientModel",
    "CancerCaseModel",
    "SpecimenModel",
    "SequencingTestModel",
    "UploadedFileModel",
    "VariantModel",
    "GeneModel",
    "ProteinModel",
    "PathwayModel",
    "DrugModel",
    "DrugTargetModel",
    "EvidenceModel",
    "DrugCandidateModel",
    "PublicationModel",
    "ClinicalTrialModel",
    "AnalysisRunModel",
    "ReportModel",
    "ConsentModel",
    "AuditLogModel",
    # Pydantic
    "PatientCreate",
    "PatientUpdate",
    "PatientResponse",
    "PatientListResponse",
    "CancerCaseCreate",
    "CancerCaseUpdate",
    "CancerCaseResponse",
    "CancerCaseListResponse",
    "SpecimenCreate",
    "SpecimenUpdate",
    "SpecimenResponse",
    "SequencingTestCreate",
    "SequencingTestResponse",
    "UploadedFileCreate",
    "UploadedFileResponse",
    "VariantImport",
    "VariantImportBatch",
    "VariantResponse",
    "VariantListResponse",
    "GeneCreate",
    "GeneResponse",
    "DrugCreate",
    "DrugResponse",
    "EvidenceCreate",
    "EvidenceResponse",
    "EvidenceSearchResult",
    "DrugCandidateResponse",
    "DrugCandidateListResponse",
    "AnalysisRunCreate",
    "AnalysisRunResponse",
    "ConsentCreate",
    "ConsentResponse",
    "AuditLogEntry",
    "GraphNode",
    "GraphEdge",
    "VisualizationGraph",
    "GraphAnalysisResponse",
    "NODE_TYPES",
    "EDGE_TYPES",
    # Auth
    "UserModel",
    "TokenBlacklistModel",
    "UserCreate",
    "UserResponse",
    "TokenResponse",
    "LoginRequest",
    "RefreshRequest",
    "LogoutRequest",
    # Case ACL
    "CaseACLModel",
    "CaseRole",
    "CASE_ROLE_HIERARCHY",
    "CASE_REQUIRED_ROLES",
    "CaseACLCreate",
    "CaseACLResponse",
    "CasePermissionCheck",
]
