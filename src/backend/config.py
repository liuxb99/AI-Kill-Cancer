import logging
import os
from pathlib import Path


def _sqlite_database_url(path: str) -> str:
    """Build an async SQLite URL for local/demo/research use."""
    raw = path.strip()
    if raw in {"", ":memory:"}:
        return "sqlite+aiosqlite:///:memory:"
    normalized = Path(raw).expanduser().as_posix()
    return f"sqlite+aiosqlite:///{normalized}"


def _running_on_vercel() -> bool:
    """Return True inside a Vercel build/runtime without requiring project env vars.

    Vercel injects VERCEL=1 automatically.  Using that platform signal keeps the
    demo API serverless-safe even when project-level DATABASE_URL / DB_BACKEND
    variables are absent or `vercel pull` does not materialize values declared in
    vercel.json.
    """
    return os.getenv("VERCEL", "").strip().lower() in {"1", "true", "yes"}


def _database_url_from_environment() -> str:
    explicit = os.getenv("DATABASE_URL", "").strip()
    if explicit:
        return explicit

    backend_env = os.getenv("DB_BACKEND", "").strip().lower()
    if backend_env:
        backend = backend_env
    elif _running_on_vercel():
        # Vercel demo deployments must never silently fall back to localhost
        # PostgreSQL.  Serverless instances have a writable /tmp directory, so an
        # ephemeral SQLite database is the safe zero-configuration default.
        backend = "sqlite"
    else:
        backend = "postgresql"

    if backend == "sqlite":
        default_path = "/tmp/ai-kill-cancer.db" if _running_on_vercel() else "./data/ai-kill-cancer.db"
        return _sqlite_database_url(os.getenv("SQLITE_PATH", default_path))
    if backend != "postgresql":
        raise ValueError("DB_BACKEND must be 'postgresql' or 'sqlite'")

    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5432"))
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")
    name = os.getenv("DB_NAME", "cancer_db")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"


class Settings:
    APP_NAME: str = "AI-Kill-Cancer — Precision Oncology Platform"
    APP_VERSION: str = "1.0.2"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # 运行模式: demo / research / local / production
    APP_MODE: str = os.getenv("APP_MODE", "demo").lower()

    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    # production 模式下禁止通配符 origin
    if CORS_ORIGINS == ["*"] and APP_MODE == "production":
        logging.warning("CORS_ORIGINS=* is not allowed in production mode, falling back to http://localhost:5173")
        CORS_ORIGINS = ["http://localhost:5173"]

    DB_BACKEND: str = os.getenv(
        "DB_BACKEND",
        "sqlite" if _running_on_vercel() else "postgresql",
    ).strip().lower()
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
    DB_NAME: str = os.getenv("DB_NAME", "cancer_db")
    SQLITE_PATH: str = os.getenv(
        "SQLITE_PATH",
        "/tmp/ai-kill-cancer.db" if _running_on_vercel() else "./data/ai-kill-cancer.db",
    )
    DATABASE_URL: str = _database_url_from_environment()

    # Bundled synthetic demo dataset. Enabled by default only in demo mode.
    DEMO_DATA_DIR: str = os.getenv("DEMO_DATA_DIR", "./data/demo")
    DEMO_AUTO_BOOTSTRAP: bool = os.getenv(
        "DEMO_AUTO_BOOTSTRAP",
        "true" if APP_MODE == "demo" else "false",
    ).lower() == "true"

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
        self._validate_database_mode()
        self._validate_jwt_secret()

    def _validate_database_mode(self):
        """SQLite is the local-first backend and may also back the ephemeral demo runtime."""
        if self.DATABASE_URL.startswith("sqlite") and self.APP_MODE == "production":
            raise ValueError(
                "SQLite is supported for local/demo/research mode only. "
                "Production mode requires an explicit scale-out backend."
            )

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
