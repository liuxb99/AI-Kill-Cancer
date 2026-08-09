from __future__ import annotations

from pathlib import Path

from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


def is_sqlite_url(db_url: str) -> bool:
    return make_url(db_url).get_backend_name() == "sqlite"


def _is_memory_sqlite(db_url: str) -> bool:
    url = make_url(db_url)
    return url.get_backend_name() == "sqlite" and url.database in {None, "", ":memory:"}


def _prepare_sqlite_file(db_url: str) -> None:
    url = make_url(db_url)
    if url.get_backend_name() != "sqlite" or url.database in {None, "", ":memory:"}:
        return
    database_path = Path(url.database).expanduser()
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
            # A single connection keeps an in-memory SQLite schema alive for the
            # entire test/local process instead of recreating an empty DB per checkout.
            kwargs["poolclass"] = StaticPool

    db_engine = create_async_engine(db_url, **kwargs)
    if is_sqlite_url(db_url):
        event.listen(db_engine.sync_engine, "connect", _enable_sqlite_pragmas)
    return db_engine


async def get_db():
    if async_session_factory is None:
        raise RuntimeError("Database not initialized")
    async with async_session_factory() as session:
        try:
            yield session
            # REVIEW-PHASE3F0-R3-P0-01 / OPEN
            # 問題：目前 get_db() 會在請求成功後自動 commit，但 EvidenceIngestionService、
            # VariantIngestionService 等 Service 也自行 commit/rollback，造成同一請求存在
            # 兩個 transaction owner，與 Phase 3F-0 選定的「Service 層明確管理交易」模式衝突。
            # 修改：統一 transaction ownership。若採 Service-owned transaction，移除此處的
            # 自動 commit，並盤點所有直接注入 db 的寫入 endpoint，確保它們改由 Service 管理；
            # 不得以 dependency auto-commit 補救缺少 Service transaction 的 API。
            # 驗證：新增測試證明 (1) Service 成功只 commit 一次；(2) Service 後段失敗完整
            # rollback；(3) endpoint 在 Service 返回後發生例外時，不會留下部分提交資料。
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db(db_url: str, debug: bool = False):
    global engine, async_session_factory
    await close_db()
    engine = _create_engine(db_url, debug)
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Import domain modules before create_all so the local SQLite database sees
    # the same ORM metadata as the API, including the PTC research extensions.
    import src.backend.domain  # noqa: F401
    import src.backend.domain.clinical_graph_outbox  # noqa: F401
    import src.backend.domain.ptc_integrated  # noqa: F401
    import src.backend.domain.ptc_knowledge  # noqa: F401
    import src.backend.domain.ptc_research  # noqa: F401
    from src.backend.database.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if is_sqlite_url(db_url):
            enabled = (await conn.execute(text("PRAGMA foreign_keys"))).scalar_one()
            if enabled != 1:
                raise RuntimeError("SQLite foreign key enforcement is not enabled")


async def close_db():
    global engine, async_session_factory
    current = engine
    engine = None
    async_session_factory = None
    if current is not None:
        await current.dispose()
