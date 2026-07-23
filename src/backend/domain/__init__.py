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

from src.backend.domain.analysis_run import (
    AnalysisRunCreate,
    AnalysisRunModel,
    AnalysisRunResponse,
)
from src.backend.domain.audit_log import (
    AuditLogEntry,
    AuditLogModel,
)
from src.backend.domain.cancer_case import (
    CancerCaseCreate,
    CancerCaseListResponse,
    CancerCaseModel,
    CancerCaseResponse,
    CancerCaseUpdate,
)
from src.backend.domain.case_acl import (
    CASE_REQUIRED_ROLES,
    CASE_ROLE_HIERARCHY,
    CaseACLCreate,
    CaseACLModel,
    CaseACLResponse,
    CasePermissionCheck,
    CaseRole,
)
from src.backend.domain.clinical_trial import ClinicalTrialModel
from src.backend.domain.consent import (
    ConsentCreate,
    ConsentModel,
    ConsentResponse,
)
from src.backend.domain.drug import (
    DrugCreate,
    DrugModel,
    DrugResponse,
    DrugTargetModel,
)
from src.backend.domain.drug_candidate import (
    DrugCandidateListResponse,
    DrugCandidateModel,
    DrugCandidateResponse,
)
from src.backend.domain.enums import (
    AnalysisModeEnum,
    AnalysisResultTypeEnum,
    AnalysisStatusEnum,
    AuditActionEnum,
    CancerTypeEnum,
    CandidateCategoryEnum,
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
from src.backend.domain.evidence import (
    EvidenceCreate,
    EvidenceModel,
    EvidenceResponse,
    EvidenceSearchResult,
)
from src.backend.domain.gene import (
    GeneCreate,
    GeneModel,
    GeneResponse,
    PathwayModel,
    ProteinModel,
)
from src.backend.domain.patient import (
    PatientCreate,
    PatientListResponse,
    PatientModel,
    PatientResponse,
    PatientUpdate,
)
from src.backend.domain.publication import PublicationModel
from src.backend.domain.report import ReportModel
from src.backend.domain.sequencing import (
    SequencingTestCreate,
    SequencingTestModel,
    SequencingTestResponse,
)
from src.backend.domain.specimen import (
    SpecimenCreate,
    SpecimenModel,
    SpecimenResponse,
    SpecimenUpdate,
)
from src.backend.domain.uploaded_file import (
    UploadedFileCreate,
    UploadedFileModel,
    UploadedFileResponse,
)
from src.backend.domain.user import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenBlacklistModel,
    TokenResponse,
    UserCreate,
    UserModel,
    UserResponse,
)
from src.backend.domain.variant import (
    VariantImport,
    VariantImportBatch,
    VariantListResponse,
    VariantModel,
    VariantResponse,
)
from src.backend.domain.visualization_graph import (
    EDGE_TYPES,
    NODE_TYPES,
    GraphAnalysisResponse,
    GraphEdge,
    GraphNode,
    VisualizationGraph,
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
