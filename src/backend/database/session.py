import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

logger = logging.getLogger(__name__)

engine = None
async_session_factory = None

_DIAG_PATH = "/tmp/db_diag.log"


def _diag(msg: str) -> None:
    """Write diagnostic message using shell echo (most robust across environments)."""
    import os
    try:
        os.system(f"echo 'DIAG:{msg}' >> /tmp/pg-diag.log 2>/dev/null")
    except Exception:
        pass


async def get_db():
    if async_session_factory is None:
        _diag("DB_ERROR: async_session_factory is None")
        logger.error("DB_ERROR: async_session_factory is None")
        raise RuntimeError("Database not initialized")
    _diag(f"DB_OK: factory={async_session_factory}")
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db(db_url: str, debug: bool = False):
    global engine, async_session_factory
    _diag(f"INIT_DB: url={db_url[:60]}...")
    engine = create_async_engine(db_url, echo=debug)
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        from src.backend.database.models import Base
        await conn.run_sync(Base.metadata.create_all)
    _diag("INIT_DB: success")


async def close_db():
    global engine, async_session_factory
    _diag("CLOSE_DB: disposing engine")
    if engine:
        await engine.dispose()
    engine = None
    async_session_factory = None
    _diag("CLOSE_DB: engine/session reset to None")
