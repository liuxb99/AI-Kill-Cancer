import logging
import sys

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.api.routes import router
from src.backend.api.research import router as research_router
from src.backend.config import settings
from src.backend.database.session import init_db, close_db

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    db_url = settings.DATABASE_URL
    if db_url:
        try:
            await init_db(db_url, debug=settings.DEBUG)
            logger.info("Database connected and tables initialized")
        except Exception as e:
            logger.warning("Database initialization failed (API will work, DB features disabled): %s", e)
    if settings.MODEL_ENABLED:
        logger.info("Model path: %s", settings.MODEL_PATH)
    yield
    await close_db()
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
