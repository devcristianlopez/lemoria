"""Shared test fixtures for Lemoria tests."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models.base import Base
from database.models import *  # noqa: F401, F403 — ensure all models are loaded


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def project(db_session):
    """Create a test project."""
    from database.models.project import Project
    p = Project(name="test-project", description="Test project")
    db_session.add(p)
    db_session.commit()
    return p


@pytest.fixture
def prd(db_session, project):
    """Create a test PRD."""
    from database.models.prd import PRD
    p = PRD(project_id=project.id, title="Test PRD", content="Test content")
    db_session.add(p)
    db_session.commit()
    return p


@pytest.fixture
def flow_engine(db_session):
    """Create a FlowEngine for testing."""
    from lemoria.flow import FlowEngine
    return FlowEngine(db_session)
