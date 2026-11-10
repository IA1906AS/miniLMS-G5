import re
from collections.abc import Generator

import psycopg
from psycopg import sql
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError as SQLAlchemyOperationalError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from uv_demo.config import settings
from uv_demo.services.backoff import exponential_backoff

_is_sqlite = "sqlite" in settings.DATABASE_URL

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=not _is_sqlite,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


@exponential_backoff(
    max_retries=3,
    base_delay=0.5,
    max_delay=5.0,
    retryable_exceptions=(psycopg.OperationalError, SQLAlchemyOperationalError),
)
def ensure_database_ready() -> None:
    """Tự động khởi tạo database trên PostgreSQL với cơ chế Exponential Backoff."""
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
                stmt = sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_db))
                cur.execute(stmt)  # nosemgrep


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
