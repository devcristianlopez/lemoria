from sqlalchemy.orm import Session
from database.models.project import Project


class ProjectService:
    def __init__(self, session: Session):
        self.session = session

    def create(self, name: str, description: str | None = None, repo_url: str | None = None) -> Project:
        project = Project(name=name, description=description, repo_url=repo_url)
        self.session.add(project)
        self.session.commit()
        return project

    def get(self, project_id: str) -> Project | None:
        return self.session.get(Project, project_id)

    def list(self, active_only: bool = True) -> list[Project]:
        query = self.session.query(Project)
        if active_only:
            query = query.filter(Project.active.is_(True))
        return query.all()

    def deactivate(self, project_id: str) -> None:
        project = self.get(project_id)
        if project:
            project.active = False
            self.session.commit()
