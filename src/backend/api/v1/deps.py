"""
Common dependencies for API v1 routes.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.session import get_db
from src.backend.repositories import (
    PatientRepository,
    CancerCaseRepository,
    SpecimenRepository,
    SequencingTestRepository,
    UploadedFileRepository,
    VariantRepository,
    DrugRepository,
    EvidenceRepository,
    AnalysisRunRepository,
    ReportRepository,
)


async def get_patient_repo(db: AsyncSession = Depends(get_db)) -> PatientRepository:
    return PatientRepository(db)


async def get_cancer_case_repo(db: AsyncSession = Depends(get_db)) -> CancerCaseRepository:
    return CancerCaseRepository(db)


async def get_specimen_repo(db: AsyncSession = Depends(get_db)) -> SpecimenRepository:
    return SpecimenRepository(db)


async def get_sequencing_repo(db: AsyncSession = Depends(get_db)) -> SequencingTestRepository:
    return SequencingTestRepository(db)


async def get_upload_repo(db: AsyncSession = Depends(get_db)) -> UploadedFileRepository:
    return UploadedFileRepository(db)


async def get_variant_repo(db: AsyncSession = Depends(get_db)) -> VariantRepository:
    return VariantRepository(db)


async def get_drug_repo(db: AsyncSession = Depends(get_db)) -> DrugRepository:
    return DrugRepository(db)


async def get_evidence_repo(db: AsyncSession = Depends(get_db)) -> EvidenceRepository:
    return EvidenceRepository(db)


async def get_analysis_run_repo(db: AsyncSession = Depends(get_db)) -> AnalysisRunRepository:
    return AnalysisRunRepository(db)


async def get_report_repo(db: AsyncSession = Depends(get_db)) -> ReportRepository:
    return ReportRepository(db)
