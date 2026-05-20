from pathlib import Path
import time

from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()

sqlite_path = settings.sqlite_path
if sqlite_path is not None:
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    from src.models import entities  # noqa: F401

    if engine.dialect.name == "postgresql":
        lock_id = 739112401
        last_exc: Exception | None = None
        for attempt in range(6):
            try:
                with engine.begin() as conn:
                    conn.execute(text("SELECT pg_advisory_lock(:lock_id)"), {"lock_id": lock_id})
                    try:
                        Base.metadata.create_all(bind=conn)
                    finally:
                        conn.execute(
                            text("SELECT pg_advisory_unlock(:lock_id)"),
                            {"lock_id": lock_id},
                        )
                return
            except (OperationalError, DBAPIError) as exc:
                last_exc = exc
                if attempt >= 5:
                    raise
                time.sleep(0.5 * (attempt + 1))

        if last_exc is not None:
            raise last_exc

    Base.metadata.create_all(bind=engine)
