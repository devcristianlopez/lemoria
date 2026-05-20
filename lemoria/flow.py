from sqlalchemy.orm import Session
from database.models.prd import PRD
from database.models.spec import Spec
from database.models.task import Task
from database.models.decision import Decision
from database.models.project import Project
from .orchestrator import Orchestrator


class FlowEngine:
    STEPS = ["idea", "spec", "prd", "tasks", "architecture", "implementation", "testing", "review", "commit", "push", "documentation", "memory_update"]

    def __init__(self, session: Session):
        self.session = session
        self.orchestrator = Orchestrator(session)

    def start_flow(self, project_id: str, idea: str) -> PRD:
        prd = PRD(project_id=project_id, title=idea[:100], content=idea, status="draft")
        self.session.add(prd)
        self.session.commit()
        return prd

    def add_spec(self, prd_id: str, title: str, content: str, order: int = 0) -> Spec:
        spec = Spec(prd_id=prd_id, title=title, content=content, order=order)
        self.session.add(spec)
        self.session.commit()
        return spec

    def create_task(self, project_id: str, prd_id: str, spec_id: str | None, title: str, agent_id: str | None = None) -> Task:
        task = Task(project_id=project_id, prd_id=prd_id, spec_id=spec_id, title=title, agent_id=agent_id)
        self.session.add(task)
        self.session.commit()
        return task

    def record_decision(self, project_id: str, title: str, description: str, rationale: str | None = None) -> Decision:
        decision = Decision(project_id=project_id, title=title, description=description, rationale=rationale)
        self.session.add(decision)
        self.session.commit()
        return decision

    def advance(self, prd_id: str) -> None:
        prd = self.session.get(PRD, prd_id)
        if prd and prd.status == "draft":
            prd.status = "active"
            self.session.commit()

    def complete(self, prd_id: str) -> None:
        prd = self.session.get(PRD, prd_id)
        if prd:
            prd.status = "completed"
            self.session.commit()
