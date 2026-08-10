from __future__ import annotations

from pathlib import Path

from sqlalchemy import event, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None
database_initialized = False
database_initialization_error: str | None = None


def is_sqlite_url(db_url: str) -> bool:
    return make_url(db_url).get_backend_name() == "sqlite"


def _is_memory_sqlite(db_url: str) -> bool:
    url = make_url(db_url)
    return url.get_backend_name() == "sqlite" and url.database in {None, "", ":memory:"}


def _sqlite_file_path(db_url: str) -> Path | None:
    url = make_url(db_url)
    if url.get_backend_name() != "sqlite" or url.database in {None, "", ":memory:"}:
        return None
    return Path(url.database).expanduser().resolve()


def _prepare_sqlite_file(db_url: str) -> None:
    database_path = _sqlite_file_path(db_url)
    if database_path is None:
        return
    database_path.parent.mkdir(parents=True, exist_ok=True)


def _enable_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
    finally:
        cursor.close()


def _create_engine(db_url: str, debug: bool) -> AsyncEngine:
    kwargs: dict[str, object] = {"echo": debug, "pool_pre_ping": True}
    if is_sqlite_url(db_url):
        _prepare_sqlite_file(db_url)
        if _is_memory_sqlite(db_url):
            kwargs["poolclass"] = StaticPool

    db_engine = create_async_engine(db_url, **kwargs)
    if is_sqlite_url(db_url):
        event.listen(db_engine.sync_engine, "connect", _enable_sqlite_pragmas)
    return db_engine


def _schema_upgrade_required(sync_connection, metadata) -> bool:
    """Return True when create_all will add at least one table or column.

    create_all cannot perform destructive migrations, but adding schema objects still
    changes a persistent research workspace.  We therefore snapshot first whenever
    the current SQLite schema is non-empty and differs from ORM metadata.
    """
    inspector = inspect(sync_connection)
    existing_tables = set(inspector.get_table_names())
    if not existing_tables:
        return False
    expected_tables = set(metadata.tables)
    if expected_tables - existing_tables:
        return True
    for table_name in expected_tables & existing_tables:
        existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
        expected_columns = {column.name for column in metadata.tables[table_name].columns}
        if expected_columns - existing_columns:
            return True
    return False


def database_status() -> dict[str, object]:
    """Return a credential-safe database startup diagnostic."""
    from src.backend.config import settings

    try:
        backend = make_url(settings.DATABASE_URL).get_backend_name()
    except Exception:
        backend = "unknown"
    return {
        "ready": database_initialized and async_session_factory is not None,
        "backend": backend,
        "mode": settings.APP_MODE,
        "error": database_initialization_error,
    }


async def ensure_db_initialized() -> None:
    """Ensure schema initialization completed before serving a DB-backed request."""
    if database_initialized and async_session_factory is not None:
        return

    from src.backend.config import settings

    try:
        await init_db(settings.DATABASE_URL, debug=settings.DEBUG)
    except Exception as exc:
        raise RuntimeError(
            f"Database initialization failed: {type(exc).__name__}: {exc}"
        ) from exc


async def get_db():
    try:
        await ensure_db_initialized()
    except Exception as exc:
        from fastapi import HTTPException

        status = database_status()
        raise HTTPException(
            status_code=503,
            detail={
                "error": "database_initialization_failed",
                "message": str(exc),
                "database": status,
            },
        ) from exc

    if async_session_factory is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=503,
            detail={
                "error": "database_not_initialized",
                "database": database_status(),
            },
        )
    async with async_session_factory() as session:
        try:
            yield session
            # REVIEW-PHASE3F0-R3-P0-01 / OPEN
            # Transaction ownership remains tracked separately from the SQLite
            # local-first hardening work in v0.3.0.
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db(db_url: str, debug: bool = False):
    global engine, async_session_factory, database_initialized, database_initialization_error
    await close_db()
    database_initialization_error = None
    try:
        engine = _create_engine(db_url, debug)
        async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        import src.backend.domain  # noqa: F401
        import src.backend.domain.clinical_graph_outbox  # noqa: F401
        import src.backend.domain.ptc_integrated  # noqa: F401
        import src.backend.domain.ptc_knowledge  # noqa: F401
        import src.backend.domain.ptc_research  # noqa: F401
        import src.backend.domain.research_depth  # noqa: F401
        from src.backend.database.models import Base

        from src.backend.config import settings

        sqlite_path = _sqlite_file_path(db_url)
        persistent_local = (
            sqlite_path is not None
            and sqlite_path.is_file()
            and settings.APP_MODE in {"local", "research"}
        )

        async with engine.begin() as conn:
            upgrade_required = False
            if persistent_local:
                upgrade_required = await conn.run_sync(
                    lambda sync_conn: _schema_upgrade_required(sync_conn, Base.metadata)
                )
            if upgrade_required and sqlite_path is not None:
                # Close the schema-inspection transaction before taking SQLite's
                # online backup. The backup is integrity-checked and timestamped.
                await conn.rollback()

        if persistent_local and upgrade_required and sqlite_path is not None:
            from src.backend.database.sqlite_workspace import backup_sqlite_database

            backup_sqlite_database(sqlite_path)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            if is_sqlite_url(db_url):
                enabled = (await conn.execute(text("PRAGMA foreign_keys"))).scalar_one()
                if enabled != 1:
                    raise RuntimeError("SQLite foreign key enforcement is not enabled")

        if (
            is_sqlite_url(db_url)
            and settings.APP_MODE == "demo"
            and settings.DEMO_AUTO_BOOTSTRAP
            and async_session_factory is not None
        ):
            from src.backend.demo import bootstrap_demo_dataset

            await bootstrap_demo_dataset(async_session_factory, settings.DEMO_DATA_DIR)

        database_initialized = True
    except Exception as exc:
        database_initialization_error = f"{type(exc).__name__}: {exc}"
        database_initialized = False
        raise


async def close_db():
    global engine, async_session_factory, database_initialized
    current = engine
    engine = None
    async_session_factory = None
    database_initialized = False
    if current is not None:
        await current.dispose()
