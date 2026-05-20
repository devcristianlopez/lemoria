from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .config import settings
from database.models.base import Base

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, class_=Session)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    return SessionLocal()
