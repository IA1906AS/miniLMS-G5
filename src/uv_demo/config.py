import os
from pathlib import Path


class Settings:
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", "lms-super-secret-key-change-in-production-2026"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    RESET_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./lms.db")
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
