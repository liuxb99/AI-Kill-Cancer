from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

engine = None
async_session_factory = None


async def get_db():
    if async_session_factory is None:
        print("DB_ERROR: async_session_factory is None", flush=True)
        raise RuntimeError("Database not initialized")
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
    print(f"INIT_DB: url={db_url[:50]}...", flush=True)
    engine = create_async_engine(db_url, echo=debug)
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        from src.backend.database.models import Base
        await conn.run_sync(Base.metadata.create_all)
    print("INIT_DB: success", flush=True)


async def close_db():
    global engine, async_session_factory
    print("CLOSE_DB: disposing engine", flush=True)
    if engine:
        await engine.dispose()
    engine = None
    async_session_factory = None
    print("CLOSE_DB: engine reset to None", flush=True)
