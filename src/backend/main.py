import logging
import sys

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.backend.api.routes import router
from src.backend.api.research import router as research_router
from src.backend.config import settings

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

engine = None
async_session_factory = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine, async_session_factory
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    db_url = settings.DATABASE_URL
    if db_url:
        engine = create_async_engine(db_url, echo=settings.DEBUG, pool_size=5, max_overflow=10)
        async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with engine.begin() as conn:
            from src.backend.database.models import Base
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database connected and tables initialized")
    if settings.MODEL_ENABLED:
        logger.info("Model path: %s", settings.MODEL_PATH)
    yield
    if engine:
        await engine.dispose()
        logger.info("Database connection closed")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    app.include_router(research_router)

    return app


app = create_app()
