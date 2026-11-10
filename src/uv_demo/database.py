import re
from collections.abc import Generator

import psycopg
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from uv_demo.config import settings

_is_sqlite = "sqlite" in settings.DATABASE_URL

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=not _is_sqlite,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def ensure_database_ready() -> None:
    """Tự động khởi tạo database trên PostgreSQL nếu chưa tồn tại."""
    if _is_sqlite:
        return
    url = make_url(settings.DATABASE_URL)
    target_db = url.database or "minilms"
    if not re.match(r"^[A-Za-z0-9_]+$", target_db):
        return
    admin_dsn = (
        f"host={url.host or '127.0.0.1'} "
        f"port={url.port or 5432} "
        f"user={url.username or 'postgres'} "
        f"password={url.password or ''} "
        f"dbname=postgres"
    )
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
            if cur.fetchone() is None:
                cur.execute(f'CREATE DATABASE "{target_db}"')


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
