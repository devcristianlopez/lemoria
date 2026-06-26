"""Tests for ProjectService."""

import pytest
from database.models.project import Project


class TestProjectService:
    """Test the project CRUD operations."""

    def test_create_project(self, db_session):
        """Should create a project with name and description."""
        from lemoria.project import ProjectService
        svc = ProjectService(db_session)
        p = svc.create("my-project", "My test project")
        assert p.name == "my-project"
        assert p.description == "My test project"
        assert p.active is True
        assert p.id is not None

    def test_create_project_no_description(self, db_session):
        """Should create a project without description."""
        from lemoria.project import ProjectService
        svc = ProjectService(db_session)
        p = svc.create("minimal")
        assert p.name == "minimal"
        assert p.description is None

    def test_get_project(self, db_session):
        """Should retrieve a project by ID."""
        from lemoria.project import ProjectService
        svc = ProjectService(db_session)
        created = svc.create("test", "desc")
        retrieved = svc.get(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "test"

    def test_get_project_not_found(self, db_session):
        """Should return None for non-existent project."""
        from lemoria.project import ProjectService
        svc = ProjectService(db_session)
        assert svc.get("nonexistent-id") is None

    def test_list_projects(self, db_session):
        """Should list all active projects."""
        from lemoria.project import ProjectService
        svc = ProjectService(db_session)
        svc.create("p1")
        svc.create("p2")
        projects = svc.list()
        assert len(projects) == 2

    def test_list_projects_empty(self, db_session):
        """Should return empty list when no projects exist."""
        from lemoria.project import ProjectService
        svc = ProjectService(db_session)
        assert svc.list() == []


class TestProjectModel:
    """Test the Project model directly."""

    def test_project_defaults(self, db_session):
        """Should have correct default values."""
        p = Project(name="defaults")
        db_session.add(p)
        db_session.commit()
        assert p.active is True
        assert p.id is not None
        assert p.created_at is not None
        assert p.updated_at is not None
