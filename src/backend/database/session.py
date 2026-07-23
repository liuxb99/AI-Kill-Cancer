from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

engine = None
async_session_factory = None


async def get_db():
    if async_session_factory is None:
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
    engine = create_async_engine(db_url, echo=debug)
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        from src.backend.database.models import Base
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    global engine
    if engine:
        await engine.dispose()
