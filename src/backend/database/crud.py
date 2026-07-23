import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.models import (
    CancerStageEnum,
    Diagnosis,
    Drug,
    GenderEnum,
    Patient,
    ResearchPaper,
    Treatment,
    TreatmentStatusEnum,
)

# ─── Patient CRUD ─────────────────────────────────────────────────────────────

async def create_patient(
    db: AsyncSession,
    name: str,
    age: int,
    gender: GenderEnum,
    biomarkers: dict | None = None,
    family_history: list[str] | None = None,
    smoking_history: str | None = None,
) -> Patient:
    patient = Patient(
        name=name,
        age=age,
        gender=gender,
        biomarkers=biomarkers or {},
        family_history=family_history or [],
        smoking_history=smoking_history,
    )
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient


async def get_patient(db: AsyncSession, patient_id: uuid.UUID) -> Patient | None:
    stmt = select(Patient).where(Patient.id == patient_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_patients(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    name: str | None = None,
    cancer_type: str | None = None,
) -> list[Patient]:
    stmt = select(Patient)
    if name:
        stmt = stmt.where(Patient.name.ilike(f"%{name}%"))
    if cancer_type:
        stmt = stmt.join(Patient.diagnoses).where(Diagnosis.cancer_type == cancer_type)
    stmt = stmt.offset(skip).limit(limit).order_by(Patient.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_patient(
    db: AsyncSession,
    patient_id: uuid.UUID,
    **kwargs,
) -> Patient | None:
    patient = await get_patient(db, patient_id)
    if not patient:
        return None
    for field, value in kwargs.items():
        if hasattr(patient, field) and value is not None:
            setattr(patient, field, value)
    await db.commit()
    await db.refresh(patient)
    return patient


async def delete_patient(db: AsyncSession, patient_id: uuid.UUID) -> bool:
    patient = await get_patient(db, patient_id)
    if not patient:
        return False
    await db.delete(patient)
    await db.commit()
    return True


async def count_patients(db: AsyncSession) -> int:
    stmt = select(func.count(Patient.id))
    result = await db.execute(stmt)
    return result.scalar() or 0


# ─── Diagnosis CRUD ───────────────────────────────────────────────────────────

async def create_diagnosis(
    db: AsyncSession,
    patient_id: uuid.UUID,
    cancer_type: str,
    stage: CancerStageEnum,
    diagnosis_date: date | None = None,
    biomarkers_at_diagnosis: dict | None = None,
    notes: str | None = None,
) -> Diagnosis:
    diagnosis = Diagnosis(
        patient_id=patient_id,
        cancer_type=cancer_type,
        stage=stage,
        diagnosis_date=diagnosis_date or date.today(),
        biomarkers_at_diagnosis=biomarkers_at_diagnosis or {},
        notes=notes,
    )
    db.add(diagnosis)
    await db.commit()
    await db.refresh(diagnosis)
    return diagnosis


async def get_diagnoses_by_patient(
    db: AsyncSession,
    patient_id: uuid.UUID,
) -> list[Diagnosis]:
    stmt = select(Diagnosis).where(Diagnosis.patient_id == patient_id).order_by(Diagnosis.diagnosis_date.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ─── Treatment CRUD ───────────────────────────────────────────────────────────

async def create_treatment(
    db: AsyncSession,
    diagnosis_id: uuid.UUID,
    name: str,
    description: str | None = None,
    status: TreatmentStatusEnum = TreatmentStatusEnum.PLANNED,
    start_date: date | None = None,
    end_date: date | None = None,
    success_rate: float | None = None,
    side_effects: list[str] | None = None,
    estimated_cost: str | None = None,
) -> Treatment:
    treatment = Treatment(
        diagnosis_id=diagnosis_id,
        name=name,
        description=description,
        status=status,
        start_date=start_date,
        end_date=end_date,
        success_rate=success_rate,
        side_effects=side_effects or [],
        estimated_cost=estimated_cost,
    )
    db.add(treatment)
    await db.commit()
    await db.refresh(treatment)
    return treatment


async def get_treatments_by_patient(
    db: AsyncSession,
    patient_id: uuid.UUID,
) -> list[Treatment]:
    stmt = (
        select(Treatment)
        .join(Diagnosis)
        .where(Diagnosis.patient_id == patient_id)
        .order_by(Treatment.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ─── Drug CRUD ────────────────────────────────────────────────────────────────

async def create_drug(
    db: AsyncSession,
    treatment_id: uuid.UUID,
    name: str,
    generic_name: str | None = None,
    dosage: str | None = None,
    frequency: str | None = None,
    route: str | None = None,
    mechanism: str | None = None,
) -> Drug:
    drug = Drug(
        treatment_id=treatment_id,
        name=name,
        generic_name=generic_name,
        dosage=dosage,
        frequency=frequency,
        route=route,
        mechanism=mechanism,
    )
    db.add(drug)
    await db.commit()
    await db.refresh(drug)
    return drug


async def get_drugs_by_treatment(
    db: AsyncSession,
    treatment_id: uuid.UUID,
) -> list[Drug]:
    stmt = select(Drug).where(Drug.treatment_id == treatment_id).order_by(Drug.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ─── ResearchPaper CRUD ───────────────────────────────────────────────────────

async def create_research_paper(
    db: AsyncSession,
    title: str,
    authors: list[str] | None = None,
    journal: str | None = None,
    year: int | None = None,
    doi: str | None = None,
    pmid: str | None = None,
    cancer_types: list[str] | None = None,
    abstract: str | None = None,
    keywords: list[str] | None = None,
    url: str | None = None,
) -> ResearchPaper:
    paper = ResearchPaper(
        title=title,
        authors=authors or [],
        journal=journal,
        year=year,
        doi=doi,
        pmid=pmid,
        cancer_types=cancer_types or [],
        abstract=abstract,
        keywords=keywords or [],
        url=url,
    )
    db.add(paper)
    await db.commit()
    await db.refresh(paper)
    return paper


async def search_research_papers(
    db: AsyncSession,
    query: str | None = None,
    cancer_type: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[ResearchPaper]:
    stmt = select(ResearchPaper)
    if query:
        stmt = stmt.where(
            ResearchPaper.title.ilike(f"%{query}%")
            | ResearchPaper.abstract.ilike(f"%{query}%")
            | ResearchPaper.keywords.any(query)
        )
    if cancer_type:
        stmt = stmt.where(ResearchPaper.cancer_types.any(cancer_type))
    if year_from is not None:
        stmt = stmt.where(ResearchPaper.year >= year_from)
    if year_to is not None:
        stmt = stmt.where(ResearchPaper.year <= year_to)
    stmt = stmt.offset(skip).limit(limit).order_by(ResearchPaper.year.desc().nullslast(), ResearchPaper.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())
