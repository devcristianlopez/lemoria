from sqlalchemy.orm import Session

from database.models.agent import Agent
from database.models.agent_execution import AgentExecution
from database.models.context import Context
from database.models.task import Task


class UnknownAgent(LookupError):
    """An agent reference that matches nothing in the registry.

    Carries the valid names so the caller can list them: the usual mistake is
    a typo, or a readable name passed where a uuid was expected, and a bare
    "not found" sends the caller hunting through the table.
    """

    def __init__(self, ref: str, available: list[str]):
        self.ref = ref
        self.available = list(available)
        super().__init__(ref)


class Orchestrator:
    def __init__(self, session: Session):
        self.session = session

    def register_agent(self, name: str, role: str, description: str | None = None) -> Agent:
        """Idempotent by name: re-registering updates the row instead of
        inserting a second agent with the same name, so calling this twice
        (a rerun, a migration, a test) cannot double the registry."""
        agent = self.session.query(Agent).filter(Agent.name == name).one_or_none()
        if agent is None:
            agent = Agent(name=name, role=role, description=description)
            self.session.add(agent)
        else:
            agent.role = role
            agent.description = description
            agent.active = True
        self.session.commit()
        return agent

    def get_agent(self, agent_id: str) -> Agent | None:
        return self.session.get(Agent, agent_id)

    def resolve_agent(self, ref: str) -> Agent:
        """Accept either an agent's readable name or its id.

        `agents.id` is a uuid, so `lemoria task create -a implementation-agent`
        would otherwise reach Postgres as a foreign key violation -- an
        IntegrityError traceback for what is really a typo. Names are what
        humans read out of `.opencode/agents/*.md`, so both are accepted.
        """
        needle = (ref or "").strip()
        agent = self.session.query(Agent).filter(Agent.name == needle).first()
        if agent is None:
            agent = self.session.get(Agent, needle)
        if agent is None:
            raise UnknownAgent(ref, self.agent_names())
        return agent

    def agent_names(self, active_only: bool = True) -> list[str]:
        """Registered names, for error messages and shell completion."""
        query = self.session.query(Agent.name).order_by(Agent.name)
        if active_only:
            query = query.filter(Agent.active.is_(True))
        return [row[0] for row in query.all()]

    def list_agents(self, active_only: bool = True) -> list[Agent]:
        query = self.session.query(Agent)
        if active_only:
            query = query.filter(Agent.active.is_(True))
        return query.all()

    def delegate(self, agent_id: str, task_id: str, input_data: str | None = None) -> AgentExecution:
        """Assign `agent_id` to an execution. Accepts a name or a uuid, like
        `FlowEngine.create_task`: the same foreign key would reject both."""
        resolved = self.resolve_agent(agent_id).id
        execution = AgentExecution(agent_id=resolved, task_id=task_id, input_data=input_data, status="running")
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
