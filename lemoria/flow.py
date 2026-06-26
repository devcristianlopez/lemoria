from datetime import datetime, timezone
from sqlalchemy.orm import Session
from database.models.prd import PRD
from database.models.spec import Spec
from database.models.task import Task
from database.models.decision import Decision
from database.models.flow_step import FlowStep
from database.enums import FlowStepStatus
from .orchestrator import Orchestrator


class FlowEngine:
    STEPS = [
        "project", "conversation", "prd", "tasks",
        "implement", "test", "review",
        "commit", "document", "vault_sync", "consolidate", "complete"
    ]

    def __init__(self, session: Session):
        self.session = session
        self.orchestrator = Orchestrator(session)

    # ── PRD lifecycle ──

    def start_flow(self, project_id: str, idea: str) -> PRD:
        prd = PRD(project_id=project_id, title=idea[:100], content=idea, status="draft")
        self.session.add(prd)
        self.session.commit()
        return prd

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

    def list_prds(self, project_id: str) -> list[PRD]:
        return self.session.query(PRD).filter(PRD.project_id == project_id).order_by(PRD.created_at.desc()).all()

    # ── Specs ──

    def add_spec(self, prd_id: str, title: str, content: str, order: int = 0) -> Spec:
        spec = Spec(prd_id=prd_id, title=title, content=content, order=order)
        self.session.add(spec)
        self.session.commit()
        return spec

    # ── Tasks ──

    def create_task(self, project_id: str, prd_id: str, spec_id: str | None, title: str, agent_id: str | None = None) -> Task:
        task = Task(project_id=project_id, prd_id=prd_id, spec_id=spec_id, title=title, agent_id=agent_id)
        self.session.add(task)
        self.session.commit()
        return task

    def list_tasks(self, project_id: str, status: str | None = None) -> list[Task]:
        query = self.session.query(Task).filter(Task.project_id == project_id)
        if status:
            query = query.filter(Task.status == status)
        return query.order_by(Task.created_at).all()

    def set_task_status(self, task_id: str, new_status: str) -> Task | None:
        t = self.session.get(Task, task_id)
        if t:
            t.status = new_status
            self.session.commit()
        return t

    # ── Decisions ──

    def record_decision(self, project_id: str, title: str, description: str, rationale: str | None = None) -> Decision:
        decision = Decision(project_id=project_id, title=title, description=description, rationale=rationale)
        self.session.add(decision)
        self.session.commit()
        return decision

    # ── Flow steps (state machine) ──

    def _get_or_create_step(self, flow_id: str, step: str) -> FlowStep:
        """Find the latest step by name, or create a new one."""
        fs = (
            self.session.query(FlowStep)
            .filter(FlowStep.flow_id == flow_id, FlowStep.step == step)
            .order_by(FlowStep.created_at.desc())
            .first()
        )
        if fs is None:
            fs = FlowStep(flow_id=flow_id, step=step)
            self.session.add(fs)
        return fs

    def start_step(self, flow_id: str, step: str) -> FlowStep:
        """Record that a step is starting."""
        fs = self._get_or_create_step(flow_id, step)
        fs.status = FlowStepStatus.RUNNING
        fs.started_at = datetime.now(timezone.utc)
        self.session.commit()
        return fs

    def complete_step(self, flow_id: str, step: str, output: str | None = None) -> FlowStep:
        """Mark a step as completed. Creates step if it doesn't exist."""
        fs = self._get_or_create_step(flow_id, step)
        fs.status = FlowStepStatus.COMPLETED
        fs.completed_at = datetime.now(timezone.utc)
        if output:
            fs.output = output
        self.session.commit()
        return fs

    def fail_step(self, flow_id: str, step: str, error: str) -> FlowStep:
        """Mark a step as failed. Creates step if it doesn't exist."""
        fs = self._get_or_create_step(flow_id, step)
        fs.status = FlowStepStatus.FAILED
        fs.completed_at = datetime.now(timezone.utc)
        fs.output = error
        self.session.commit()
        return fs

    def get_flow_status(self, flow_id: str) -> dict:
        """Return the current status of a flow: all steps and their statuses."""
        steps = (
            self.session.query(FlowStep)
            .filter(FlowStep.flow_id == flow_id)
            .order_by(FlowStep.created_at.asc())
            .all()
        )
        if not steps:
            return {"flow_id": flow_id, "steps": [], "current_step": None, "completed": False}

        last = steps[-1]
        return {
            "flow_id": flow_id,
            "steps": [
                {"step": s.step, "status": s.status, "output": s.output, "started_at": str(s.started_at or ""), "completed_at": str(s.completed_at or "")}
                for s in steps
            ],
            "current_step": last.step if last.status in ("running", "pending") else None,
            "completed": last.status == "completed" and last.step == "complete",
        }
# Already at end of file - the fix is to replace the step methods above
