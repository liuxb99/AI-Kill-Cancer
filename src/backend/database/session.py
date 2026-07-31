from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

engine = None
async_session_factory = None


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
    engine = create_async_engine(db_url, echo=debug)
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        from src.backend.database.models import Base
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    global engine
    if engine:
        await engine.dispose()
