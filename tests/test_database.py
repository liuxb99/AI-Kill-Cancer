import uuid
import pytest
from datetime import date
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

from src.backend.database.models import (
    Base, Patient, Diagnosis, Treatment, Drug, ResearchPaper,
    GenderEnum, CancerStageEnum, TreatmentStatusEnum,
)
from src.backend.database.crud import (
    create_patient, get_patient, list_patients,
    update_patient, delete_patient, count_patients,
    create_diagnosis, get_diagnoses_by_patient,
    create_treatment, get_treatments_by_patient,
    create_drug, get_drugs_by_treatment,
    create_research_paper, search_research_papers,
)


@pytest.fixture(scope="module")
def engine():
    e = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(e, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=e)
    yield e
    Base.metadata.drop_all(bind=e)


@pytest.fixture
def session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    s = SessionLocal()
    yield s
    s.close()
    transaction.rollback()
    connection.close()


class TestPatientCRUD:

    def test_create_patient(self, session):
        p = Patient(name="Test Patient", age=45, gender=GenderEnum.M)
        session.add(p)
        session.commit()
        assert p.id is not None
        assert p.name == "Test Patient"

    def test_get_patient(self, session):
        p = Patient(name="Get Test", age=30, gender=GenderEnum.F)
        session.add(p)
        session.commit()
        fetched = session.get(Patient, p.id)
        assert fetched is not None
        assert fetched.name == "Get Test"

    def test_delete_patient(self, session):
        p = Patient(name="Delete Me", age=50, gender=GenderEnum.M)
        session.add(p)
        session.commit()
        session.delete(p)
        session.commit()
        assert session.get(Patient, p.id) is None

    def test_patient_to_dict(self, session):
        p = Patient(name="Dict Test", age=35, gender=GenderEnum.F,
                    biomarkers={"EGFR": 0.5}, smoking_history="never",
                    family_history=["Breast Cancer"])
        session.add(p)
        session.commit()
        assert p.age == 35
        assert p.gender == GenderEnum.F
        assert p.biomarkers == {"EGFR": 0.5}
        assert p.smoking_history == "never"
        assert "Breast Cancer" in (p.family_history or [])


class TestDiagnosisCRUD:

    def test_create_diagnosis(self, session):
        p = Patient(name="Diag Patient", age=60, gender=GenderEnum.M)
        session.add(p)
        session.commit()
        d = Diagnosis(
            patient_id=p.id, cancer_type="Lung Cancer",
            stage=CancerStageEnum.STAGE_2,
        )
        session.add(d)
        session.commit()
        assert d.id is not None
        assert d.cancer_type == "Lung Cancer"
        assert d.stage == CancerStageEnum.STAGE_2

    def test_diagnosis_relationships(self, session):
        p = Patient(name="Rel Patient", age=55, gender=GenderEnum.F)
        session.add(p)
        session.commit()
        d1 = Diagnosis(patient_id=p.id, cancer_type="Breast Cancer",
                       stage=CancerStageEnum.STAGE_1)
        d2 = Diagnosis(patient_id=p.id, cancer_type="Ovarian Cancer",
                       stage=CancerStageEnum.STAGE_3)
        session.add(d1)
        session.add(d2)
        session.commit()
        assert len(p.diagnoses) == 2


class TestTreatmentCRUD:

    def test_create_treatment(self, session):
        p = Patient(name="Tx Patient", age=40, gender=GenderEnum.F)
        session.add(p)
        session.commit()
        d = Diagnosis(patient_id=p.id, cancer_type="Breast Cancer",
                      stage=CancerStageEnum.STAGE_2)
        session.add(d)
        session.commit()
        t = Treatment(
            diagnosis_id=d.id, name="Chemotherapy",
            status=TreatmentStatusEnum.PLANNED,
            success_rate=0.75,
            side_effects=["Nausea", "Fatigue"],
        )
        session.add(t)
        session.commit()
        assert t.id is not None
        assert t.name == "Chemotherapy"
        assert "Nausea" in (t.side_effects or [])

    def test_treatment_status_enum(self):
        assert TreatmentStatusEnum.PLANNED.value == "planned"
        assert TreatmentStatusEnum.ONGOING.value == "ongoing"
        assert TreatmentStatusEnum.COMPLETED.value == "completed"

    def test_treatment_relationship(self, session):
        p = Patient(name="TxRel", age=50, gender=GenderEnum.M)
        session.add(p)
        session.commit()
        d = Diagnosis(patient_id=p.id, cancer_type="Lung Cancer",
                      stage=CancerStageEnum.STAGE_3)
        session.add(d)
        session.commit()
        t1 = Treatment(diagnosis_id=d.id, name="Surgery")
        t2 = Treatment(diagnosis_id=d.id, name="Radiotherapy")
        session.add(t1)
        session.add(t2)
        session.commit()
        assert len(d.treatments) == 2


class TestDrugCRUD:

    def test_create_drug(self, session):
        p = Patient(name="Drug Patient", age=55, gender=GenderEnum.F)
        session.add(p)
        session.commit()
        d = Diagnosis(patient_id=p.id, cancer_type="Lung Cancer",
                      stage=CancerStageEnum.STAGE_4)
        session.add(d)
        session.commit()
        t = Treatment(diagnosis_id=d.id, name="Targeted Therapy")
        session.add(t)
        session.commit()
        drug = Drug(
            treatment_id=t.id, name="Osimertinib",
            generic_name="AZD9291", dosage="80mg",
            frequency="QD", route="oral",
        )
        session.add(drug)
        session.commit()
        assert drug.id is not None
        assert drug.name == "Osimertinib"

    def test_drug_in_treatment(self, session):
        p = Patient(name="DrugRel", age=45, gender=GenderEnum.M)
        session.add(p)
        session.commit()
        d = Diagnosis(patient_id=p.id, cancer_type="Lung Cancer",
                      stage=CancerStageEnum.STAGE_2)
        session.add(d)
        session.commit()
        t = Treatment(diagnosis_id=d.id, name="Chemo")
        session.add(t)
        session.commit()
        drug = Drug(treatment_id=t.id, name="Cisplatin")
        session.add(drug)
        session.commit()
        assert len(t.drugs) == 1


class TestResearchPaperCRUD:

    def test_create_paper(self, session):
        paper = ResearchPaper(
            title="Test Cancer Research Paper",
            authors=["Author One", "Author Two"],
            journal="Journal of Oncology",
            year=2024,
            doi="10.1000/test.12345",
            cancer_types=["Lung Cancer"],
            abstract="This is a test abstract for testing purposes.",
        )
        session.add(paper)
        session.commit()
        assert paper.id is not None
        assert paper.title == "Test Cancer Research Paper"
        assert paper.year == 2024

    def test_paper_unique_doi(self, session):
        p1 = ResearchPaper(title="Paper 1", doi="10.1000/unique")
        session.add(p1)
        session.commit()
        with pytest.raises(Exception):
            p2 = ResearchPaper(title="Paper 2", doi="10.1000/unique")
            session.add(p2)
            session.commit()

    def test_paper_with_pmid(self, session):
        paper = ResearchPaper(
            title="PMID Test",
            pmid="12345678",
            journal="Nature",
            year=2023,
        )
        session.add(paper)
        session.commit()
        assert paper.pmid == "12345678"

    def test_paper_cancer_types(self, session):
        paper = ResearchPaper(
            title="Multi Cancer",
            cancer_types=["Lung Cancer", "Breast Cancer", "Colorectal Cancer"],
        )
        session.add(paper)
        session.commit()
        assert len(paper.cancer_types) == 3


class TestEnumValues:

    def test_gender_enum(self):
        assert GenderEnum.M.value == "M"
        assert GenderEnum.F.value == "F"

    def test_cancer_stage_enum(self):
        assert CancerStageEnum.STAGE_0.value == "0"
        assert CancerStageEnum.STAGE_4.value == "4"

    def test_treatment_status_values(self):
        assert TreatmentStatusEnum.PLANNED.value == "planned"
        assert TreatmentStatusEnum.CANCELLED.value == "cancelled"


class TestModelRepr:

    def test_patient_repr(self):
        p = Patient(id=uuid.uuid4(), name="Repr", age=30, gender=GenderEnum.M)
        assert "Patient" in repr(p)
        assert "Repr" in repr(p)

    def test_diagnosis_repr(self):
        d = Diagnosis(id=uuid.uuid4(), cancer_type="Lung Cancer",
                      stage=CancerStageEnum.STAGE_2)
        assert "Lung Cancer" in repr(d)

    def test_treatment_repr(self):
        t = Treatment(id=uuid.uuid4(), name="Chemo",
                      status=TreatmentStatusEnum.ONGOING)
        assert "Chemo" in repr(t)

    def test_drug_repr(self):
        dr = Drug(id=uuid.uuid4(), name="Test Drug")
        assert "Test Drug" in repr(dr)

    def test_paper_repr(self):
        rp = ResearchPaper(id=uuid.uuid4(), title="Short Title")
        assert "Short Title" in repr(rp)
