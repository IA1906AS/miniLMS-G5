import os
from pathlib import Path
from urllib.parse import quote_plus


def _load_dotenv() -> None:
    env_path = Path(".env")
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip("\"'"))


_load_dotenv()


def _resolve_database_url() -> str:
    raw_url = os.getenv("DATABASE_URL", "").strip()
    if not raw_url:
        pg_user = os.getenv("POSTGRES_USER", "postgres")
        pg_pass = quote_plus(os.getenv("POSTGRES_PASSWORD", "postgres"))
        pg_host = os.getenv("POSTGRES_HOST", "127.0.0.1")
        pg_port = os.getenv("POSTGRES_PORT", "5432")
        pg_db = os.getenv("POSTGRES_DB", "minilms")
        raw_url = (
            f"postgresql+psycopg://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
        )
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+psycopg://", 1)
    if raw_url.startswith("postgresql://"):
        return raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return raw_url


class Settings:
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", "lms-super-secret-key-change-in-production-2026"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    RESET_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str = _resolve_database_url()
    UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", "./uploads")).resolve()
    MAX_FILE_SIZE_BYTES: int = 15 * 1024 * 1024  # 15 MB
    ALLOWED_AVATAR_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".webp"}
    ALLOWED_SUBMISSION_EXTENSIONS: set[str] = {
        ".pdf",
        ".docx",
        ".zip",
        ".rar",
        ".py",
        ".ipynb",
        ".txt",
    }
    ALLOWED_MATERIAL_EXTENSIONS: set[str] = {
        ".pdf",
        ".docx",
        ".pptx",
        ".zip",
        ".txt",
        ".mp4",
    }


settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
