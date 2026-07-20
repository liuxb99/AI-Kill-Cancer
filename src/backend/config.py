import os
import logging


class Settings:
    APP_NAME: str = "AI-Kill-Cancer — Precision Oncology Platform"
    APP_VERSION: str = "0.3.2"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # 运行模式: demo / research / production
    APP_MODE: str = os.getenv("APP_MODE", "demo").lower()

    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    # production 模式下禁止通配符 origin
    if CORS_ORIGINS == ["*"] and APP_MODE == "production":
        logging.warning("CORS_ORIGINS=* is not allowed in production mode, falling back to http://localhost:5173")
        CORS_ORIGINS = ["http://localhost:5173"]

    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
    DB_NAME: str = os.getenv("DB_NAME", "cancer_db")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
    )

    MODEL_PATH: str = os.getenv("MODEL_PATH", "./models/cancer_prediction.pkl")
    MODEL_ENABLED: bool = os.getenv("MODEL_ENABLED", "true").lower() == "true"

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
