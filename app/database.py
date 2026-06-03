from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "root")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    name = os.getenv("POSTGRES_DB", "acko_insurance")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


def get_engine() -> Engine | None:
    global _engine, _SessionLocal
    if _engine is not None:
        return _engine
    try:
        _engine = create_engine(get_database_url(), pool_pre_ping=True)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return _engine
    except Exception:
        _engine = None
        _SessionLocal = None
        return None


@contextmanager
def get_db() -> Generator[Session, None, None]:
    if _SessionLocal is None:
        get_engine()
    if _SessionLocal is None:
        raise RuntimeError("Database unavailable")
    db = _SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def db_available() -> bool:
    return get_engine() is not None
