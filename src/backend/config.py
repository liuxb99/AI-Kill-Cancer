import logging
import os


class Settings:
    APP_NAME: str = "AI-Kill-Cancer — Precision Oncology Platform"
    APP_VERSION: str = "1.0.2"
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

    # Auth/JWT settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
    BCRYPT_ROUNDS: int = 12

    def __init__(self):
        self._validate_jwt_secret()

    def _validate_jwt_secret(self):
        """In production mode, require JWT_SECRET_KEY to be set from environment."""
        if not self.JWT_SECRET_KEY:
            if self.APP_MODE == "production":
                raise ValueError(
                    "JWT_SECRET_KEY environment variable is required in production mode. "
                    "Set it to a secure random value before starting the server."
                )
            self.JWT_SECRET_KEY = "akc-dev-jwt-secret-do-not-use-in-production"


settings = Settings()
