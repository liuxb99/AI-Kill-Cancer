import uuid
from datetime import date, datetime

from sqlalchemy import Column, String, Text, Float, Integer, Date, DateTime, ForeignKey, Enum as SAEnum, JSON, TypeDecorator
from sqlalchemy.orm import declarative_base, relationship
import enum


class CompatUUID(TypeDecorator):
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return str(value) if value else None

    def process_result_value(self, value, dialect):
        return uuid.UUID(value) if value else None


Base = declarative_base()


def _uuid():
    return uuid.uuid4()


class GenderEnum(str, enum.Enum):
    M = "M"
    F = "F"


class CancerStageEnum(str, enum.Enum):
    STAGE_0 = "0"
    STAGE_1 = "1"
    STAGE_2 = "2"
    STAGE_3 = "3"
    STAGE_4 = "4"


class TreatmentStatusEnum(str, enum.Enum):
    PLANNED = "planned"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Patient(Base):
    __tablename__ = "patients"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    name = Column(String(128), nullable=False, index=True)
    age = Column(Integer, nullable=False)
    gender = Column(SAEnum(GenderEnum), nullable=False)
    biomarkers = Column(JSON, default=dict)
    family_history = Column(JSON, default=list)
    smoking_history = Column(String(16), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    diagnoses = relationship("Diagnosis", back_populates="patient", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Patient(id={self.id}, name={self.name!r}, age={self.age})>"


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    patient_id = Column(CompatUUID, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    cancer_type = Column(String(64), nullable=False, index=True)
    stage = Column(SAEnum(CancerStageEnum), nullable=False)
    diagnosis_date = Column(Date, nullable=False, default=date.today)
    biomarkers_at_diagnosis = Column(JSON, default=dict)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    patient = relationship("Patient", back_populates="diagnoses")
    treatments = relationship("Treatment", back_populates="diagnosis", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Diagnosis(id={self.id}, cancer_type={self.cancer_type!r}, stage={self.stage})>"


class Treatment(Base):
    __tablename__ = "treatments"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    diagnosis_id = Column(CompatUUID, ForeignKey("diagnoses.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SAEnum(TreatmentStatusEnum), default=TreatmentStatusEnum.PLANNED, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    success_rate = Column(Float, nullable=True)
    side_effects = Column(JSON, default=list)
    estimated_cost = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    diagnosis = relationship("Diagnosis", back_populates="treatments")
    drugs = relationship("Drug", back_populates="treatment", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Treatment(id={self.id}, name={self.name!r}, status={self.status})>"


class Drug(Base):
    __tablename__ = "drugs"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    treatment_id = Column(CompatUUID, ForeignKey("treatments.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), nullable=False, index=True)
    generic_name = Column(String(128), nullable=True)
    dosage = Column(String(64), nullable=True)
    frequency = Column(String(64), nullable=True)
    route = Column(String(32), nullable=True)
    mechanism = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    treatment = relationship("Treatment", back_populates="drugs")

    def __repr__(self):
        return f"<Drug(id={self.id}, name={self.name!r})>"


class ResearchPaper(Base):
    __tablename__ = "research_papers"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    title = Column(String(512), nullable=False, index=True)
    authors = Column(JSON, default=list)
    journal = Column(String(256), nullable=True)
    year = Column(Integer, nullable=True)
    doi = Column(String(128), nullable=True, unique=True)
    pmid = Column(String(32), nullable=True, unique=True)
    cancer_types = Column(JSON, default=list)
    abstract = Column(Text, nullable=True)
    keywords = Column(JSON, default=list)
    url = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ResearchPaper(id={self.id}, title={self.title!r})>"
