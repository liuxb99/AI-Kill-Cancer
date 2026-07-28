import os
import sys
import uuid
from dataclasses import dataclass

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import torch

    from src.models.cancer_classifier import CancerClassifier, CancerClassifierConfig
    from src.models.train import TrainingConfig
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False


@pytest.fixture(scope="session")
def device():
    if torch is None:
        pytest.skip("PyTorch not available")
    return torch.device("cpu")


@pytest.fixture(scope="session")
def classifier_config():
    if torch is None:
        pytest.skip("PyTorch not available")
    return CancerClassifierConfig(
        input_dim=100,
        hidden_dims=(64, 32),
        dropout=0.1,
        num_cancer_types=3,
        num_subtypes=6,
        num_stages=4,
        use_batch_norm=False,
    )


@pytest.fixture(scope="session")
def classifier(classifier_config):
    if torch is None:
        pytest.skip("PyTorch not available")
    return CancerClassifier(classifier_config)


@pytest.fixture(scope="session")
def training_config():
    if torch is None:
        pytest.skip("PyTorch not available")
    return TrainingConfig(
        batch_size=8,
        learning_rate=1e-3,
        num_epochs=2,
        device="cpu",
        save_dir="tests/tmp_checkpoints",
    )


@pytest.fixture
def sample_gene_expression():
    rng = np.random.RandomState(42)
    return rng.randn(100).astype(np.float32)


@pytest.fixture
def sample_batch():
    rng = np.random.RandomState(42)
    X = rng.randn(4, 100).astype(np.float32)
    y_cancer = rng.randint(0, 3, size=4)
    y_subtype = rng.randint(0, 6, size=4)
    y_stage = rng.randint(0, 4, size=4)
    return X, y_cancer, y_subtype, y_stage


@pytest.fixture
def sample_smiles():
    return ["CCO", "CC(=O)OC1=CC=CC=C1C(=O)O", "c1ccccc1", "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O"]


@pytest.fixture
def uuid_str():
    return str(uuid.uuid4())


@pytest.fixture(autouse=True)
def cleanup_tmp(request):
    import shutil
    tmp_dir = os.path.join("tests", "tmp_checkpoints")
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)


@dataclass
class MockAsyncSession:
    added: list = None
    commited: bool = False
    _data: dict = None

    def __post_init__(self):
        self.added = []
        self._data = {}

    async def add(self, obj):
        obj.id = uuid.uuid4()
        self.added.append(obj)

    async def flush(self):
        pass

    async def commit(self):
        self.commited = True

    async def refresh(self, obj):
        pass

    async def execute(self, stmt):
        return MockResult()

    async def close(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class MockResult:
    def scalar_one_or_none(self):
        return None

    def scalars(self):
        return MockScalars()

    def scalar(self):
        return 0


class MockScalars:
    def all(self):
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# PostgreSQL Integration Test Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "pg: marks tests requiring PostgreSQL")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")


@pytest.fixture(scope="session")
def pg_engine():
    """Session-scoped sync SQLAlchemy engine for PostgreSQL integration tests."""
    import re
    from sqlalchemy import create_engine

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        pytest.skip("DATABASE_URL environment variable not set — requires PostgreSQL")

    # Strip async driver suffix to get sync variant (same as migrations/env.py)
    sync_url = re.sub(r"\+asyncpg|\+aiosqlite|\+aiomysql|\+aioodbc|\+asyncmy", "", db_url)

    # Ensure we use psycopg2 for PostgreSQL sync driver
    if sync_url.startswith("postgresql://") and "+psycopg2" not in sync_url:
        sync_url = sync_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    engine = create_engine(sync_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def pg_connection(pg_engine):
    """提供 PostgreSQL 同步連接，用於 integration 測試。"""
    connection = pg_engine.connect()
    yield connection
    connection.close()


@pytest.fixture
def alembic_runner(pg_engine):
    """提供 alembic upgrade/downgrade 執行器。"""
    from alembic import command
    from alembic.config import Config

    def _run(operation: str, revision: str):
        """執行 alembic operation (upgrade/downgrade) 到指定 revision。"""
        cfg = Config()
        cfg.set_main_option("script_location", "migrations")
        # 使用與 pg_engine 相同的同步 URL
        cfg.set_main_option("sqlalchemy.url", str(pg_engine.url))
        getattr(command, operation)(cfg, revision)

    return _run
