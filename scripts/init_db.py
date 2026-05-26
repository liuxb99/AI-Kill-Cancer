import argparse
import asyncio
import logging

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

from src.backend.config import settings
from src.backend.database.models import Base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def create_database_if_not_exists():
    admin_url = (
        f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/postgres"
    )
    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname = '{settings.DB_NAME}'")
            )
            if not result.scalar():
                await conn.execute(text(f'CREATE DATABASE "{settings.DB_NAME}"'))
                logger.info(f"資料庫 {settings.DB_NAME} 已建立")
            else:
                logger.info(f"資料庫 {settings.DB_NAME} 已存在")
    finally:
        await engine.dispose()


async def init_db(drop_first: bool = False):
    await create_database_if_not_exists()

    engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
    try:
        if drop_first:
            logger.warning("正在刪除所有資料表...")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            logger.info("所有資料表已刪除")

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("所有資料表已建立")

        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            result = await session.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            )
            tables = [row[0] for row in result]
            logger.info(f"已確認資料表: {', '.join(tables)}")
    finally:
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="癌症資料庫初始化腳本")
    parser.add_argument("--drop", action="store_true", help="先刪除所有資料表再重建")
    parser.add_argument("--dry-run", action="store_true", help="僅檢查連線，不執行 migration")
    args = parser.parse_args()

    if args.dry_run:
        logger.info(f"欲連線資料庫: {settings.DB_USER}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
        logger.info("僅檢查模式，未執行任何變更")
        return

    asyncio.run(init_db(drop_first=args.drop))


if __name__ == "__main__":
    main()
