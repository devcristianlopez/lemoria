from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from database.models.base import Base

from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, class_=Session)

# Columns added after the first release. create_all() creates missing tables
# but never alters an existing one, so these need explicit DDL.
#
# Table and column names are literals, never user input, so the interpolation
# is safe. IF NOT EXISTS is what makes re-running init harmless.
_ADDED_COLUMNS = (
    ("agents", "model", "VARCHAR(255)"),
    ("agents", "variant", "VARCHAR(64)"),
)


def _migrate() -> None:
    for table, column, ddl in _ADDED_COLUMNS:
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {ddl}"))


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate()


def get_session() -> Session:
    return SessionLocal()
