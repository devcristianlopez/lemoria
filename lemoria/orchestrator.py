from sqlalchemy.orm import Session
from database.models.agent import Agent
from database.models.agent_execution import AgentExecution
from database.models.task import Task
from database.models.context import Context


class Orchestrator:
    def __init__(self, session: Session):
        self.session = session

    def register_agent(self, name: str, role: str, description: str | None = None) -> Agent:
        agent = Agent(name=name, role=role, description=description)
        self.session.add(agent)
        self.session.commit()
        return agent

    def get_agent(self, agent_id: str) -> Agent | None:
        return self.session.get(Agent, agent_id)

    def list_agents(self, active_only: bool = True) -> list[Agent]:
        query = self.session.query(Agent)
        if active_only:
            query = query.filter(Agent.active.is_(True))
        return query.all()

    def delegate(self, agent_id: str, task_id: str, input_data: str | None = None) -> AgentExecution:
        execution = AgentExecution(agent_id=agent_id, task_id=task_id, input_data=input_data, status="running")
        self.session.add(execution)
        self.session.commit()
        return execution

    def complete_execution(self, execution_id: str, output_data: str | None = None, error: str | None = None) -> None:
        execution = self.session.get(AgentExecution, execution_id)
        if execution:
            execution.output_data = output_data
            execution.status = "failed" if error else "completed"
            execution.error = error
            self.session.commit()

    def get_context_for_agent(self, agent_id: str) -> list[Context]:
        tasks = self.session.query(Task).filter(
            Task.agent_id == agent_id, Task.status == "in_progress"
        ).all()
        project_ids = {t.project_id for t in tasks}
        contexts = []
        for pid in project_ids:
            contexts.extend(
                self.session.query(Context).filter(Context.project_id == pid).order_by(Context.priority.desc()).all()
            )
        return contexts
