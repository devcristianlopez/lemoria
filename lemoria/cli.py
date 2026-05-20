import click
from .core import Lemoria
from database.models.task import Task


@click.group()
def cli():
    pass


@cli.command()
def init():
    """Initialize Lemoria system (creates DB tables, vault directories)."""
    app = Lemoria()
    app.init_system()
    app.close()
    click.echo("Lemoria initialized.")


@cli.group()
def project():
    """Manage projects."""


@project.command()
@click.argument("name")
@click.option("--description", "-d", default=None)
def create(name: str, description: str | None):
    app = Lemoria()
    p = app.projects.create(name, description)
    click.echo(f"Project [{p.id[:8]}] {p.name} created.")


@project.command()
@click.argument("project_id")
def get(project_id: str):
    app = Lemoria()
    p = app.projects.get(project_id)
    if p:
        click.echo(f"  {p.id}  {p.name}")
        if p.description:
            click.echo(f"     {p.description}")
    else:
        click.echo("Project not found.")


@project.command()
def list():
    app = Lemoria()
    for p in app.projects.list():
        click.echo(f"  {p.id[:8]}  {p.name}")


@cli.group()
def conv():
    """Manage conversations."""


@conv.command()
@click.argument("project_id")
@click.option("--title", "-t", default=None)
def create(project_id: str, title: str | None):
    app = Lemoria()
    c = app.memory.create_conversation(project_id, title)
    click.echo(f"Conversation [{c.id[:8]}] created.")


@conv.command()
@click.argument("conversation_id")
@click.argument("role")
@click.argument("content")
def add(conversation_id: str, role: str, content: str):
    app = Lemoria()
    m = app.memory.add_message(conversation_id, role, content)
    click.echo(f"Message added (id={m.id[:8]}).")


@conv.command()
@click.argument("project_id")
def list(project_id: str):
    app = Lemoria()
    for c in app.memory.list_conversations(project_id):
        click.echo(f"  {c.id[:8]}  {c.title or '(no title)'}  [{c.created_at}]")


@cli.group()
def agent():
    """Manage agents."""


@agent.command()
@click.argument("name")
@click.argument("role")
@click.option("--description", "-d", default=None)
def register(name: str, role: str, description: str | None):
    app = Lemoria()
    a = app.orchestrator.register_agent(name, role, description)
    click.echo(f"Agent [{a.id[:8]}] {a.name} registered.")


@agent.command()
def list():
    app = Lemoria()
    for a in app.orchestrator.list_agents():
        click.echo(f"  {a.id[:8]}  {a.name} ({a.role})")


@cli.group()
def flow():
    """SDD workflow."""


@flow.command()
@click.argument("project_id")
@click.argument("idea")
def start(project_id: str, idea: str):
    """Create a PRD from an idea and start the SDD flow."""
    app = Lemoria()
    prd = app.flow.start_flow(project_id, idea)
    click.echo(f"Flow started. PRD [{prd.id[:8]}] created.")


@flow.command()
@click.argument("prd_id")
def advance(prd_id: str):
    """Move PRD from draft to active."""
    app = Lemoria()
    app.flow.advance(prd_id)
    click.echo(f"PRD {prd_id[:8]} advanced to active.")


@flow.command()
@click.argument("prd_id")
def complete(prd_id: str):
    """Mark PRD as completed."""
    app = Lemoria()
    app.flow.complete(prd_id)
    click.echo(f"PRD {prd_id[:8]} completed.")


@flow.command()
@click.argument("project_id")
@click.option("--status", "-s", default=None, help="Filter by status")
def list(project_id: str, status: str | None):
    """List PRDs for a project."""
    app = Lemoria()
    from database.models.prd import PRD
    query = app.session.query(PRD).filter(PRD.project_id == project_id)
    if status:
        query = query.filter(PRD.status == status)
    for p in query.order_by(PRD.created_at.desc()).all():
        click.echo(f"  {p.id[:8]}  [{p.status:10}]  {p.title[:60]}")


@cli.group()
def task():
    """Manage tasks."""


@task.command()
@click.argument("project_id")
@click.argument("prd_id")
@click.option("--title", "-t", required=True, help="Task title")
@click.option("--description", "-d", default=None, help="Task description")
@click.option("--agent-id", "-a", default=None, help="Assign to agent ID")
def create(project_id: str, prd_id: str, title: str, description: str | None, agent_id: str | None):
    app = Lemoria()
    t = app.flow.create_task(project_id, prd_id, None, title, agent_id)
    if description:
        t.description = description
        app.session.commit()
    click.echo(f"Task [{t.id[:8]}] created: {title}")


@task.command()
@click.argument("project_id")
@click.option("--status", "-s", default=None, help="Filter by status")
def list(project_id: str, status: str | None):
    app = Lemoria()
    query = app.session.query(Task).filter(Task.project_id == project_id)
    if status:
        query = query.filter(Task.status == status)
    for t in query.order_by(Task.created_at).all():
        click.echo(f"  {t.id[:8]}  [{t.status:10}]  {t.title}")


@task.command()
@click.argument("task_id")
@click.argument("new_status")
def status(task_id: str, new_status: str):
    """Update task status (pending/in_progress/completed/failed)."""
    app = Lemoria()
    t = app.session.get(Task, task_id)
    if t:
        t.status = new_status
        app.session.commit()
        click.echo(f"Task {task_id[:8]} → {new_status}")
    else:
        click.echo("Task not found.")


@cli.group()
def decision():
    """Log technical decisions."""


@decision.command()
@click.argument("project_id")
@click.option("--title", "-t", required=True, help="Decision title")
@click.option("--description", "-d", required=True, help="Decision description")
@click.option("--rationale", "-r", default=None, help="Rationale behind the decision")
def log(project_id: str, title: str, description: str, rationale: str | None):
    app = Lemoria()
    d = app.flow.record_decision(project_id, title, description, rationale)
    click.echo(f"Decision [{d.id[:8]}] logged: {title}")


@decision.command()
@click.argument("project_id")
def list(project_id: str):
    """List decisions for a project."""
    app = Lemoria()
    from database.models.decision import Decision
    for d in app.session.query(Decision).filter(Decision.project_id == project_id).order_by(Decision.created_at.desc()).all():
        click.echo(f"  {d.id[:8]}  [{d.status:10}]  {d.title}")


if __name__ == "__main__":
    cli()
