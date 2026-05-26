import os


class Settings:
    APP_NAME: str = "AI Kill Cancer API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")

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
