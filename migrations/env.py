import os
import re
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from src.backend.database.models import Base
from src.backend.domain import (
    PatientModel,
    CancerCaseModel,
    SpecimenModel,
    SequencingTestModel,
    UploadedFileModel,
    VariantModel,
    GeneModel,
    ProteinModel,
    PathwayModel,
    DrugModel,
    DrugTargetModel,
    EvidenceModel,
    DrugCandidateModel,
    PublicationModel,
    ClinicalTrialModel,
    AnalysisRunModel,
    ReportModel,
    ConsentModel,
    AuditLogModel,
)
from src.backend.domain.user import UserModel, TokenBlacklistModel
from src.backend.domain.case_acl import CaseACLModel
from src.backend.domain.ptc_research import (
    PTCImportBatchModel,
    PTCOutcomeModel,
    PTCResearchCaseModel,
    PTCVariantModel,
)
from src.backend.domain.ptc_knowledge import (
    PTCClinicalTrialModel,
    PTCEvidenceRecordModel,
    PTCTherapyModel,
    PTCTherapyTargetModel,
)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    url = config.get_main_option("sqlalchemy.url")
    sync_url = re.sub(r"\+asyncpg|\+aiosqlite|\+aiomysql|\+aioodbc|\+asyncmy", "", url)
    connectable = create_engine(sync_url)
    with connectable.connect() as connection:
        do_run_migrations(connection)
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
