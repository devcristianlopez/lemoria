import click
from .core import Lemoria
from database.models.task import Task
from database.models.project import Project
from database.models.conversation import Conversation
from database.models.prd import PRD
from database.models.decision import Decision


def _resolve_id(session, model, prefix: str) -> str | None:
    if "-" in prefix:
        return prefix
    rows = session.query(model).filter(model.id.startswith(prefix)).all()
    if len(rows) == 1:
        return rows[0].id
    if len(rows) > 1:
        click.echo(f"Error: multiple matches for '{prefix}'", err=True)
        return None
    return prefix


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
    click.echo(f"Project [{p.id}] {p.name} created.")


@project.command()
@click.argument("project_id")
def get(project_id: str):
    app = Lemoria()
    pid = _resolve_id(app.session, Project, project_id) or project_id
    p = app.projects.get(pid)
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
        click.echo(f"  {p.id}  {p.name}")


@cli.group()
def conv():
    """Manage conversations."""


@conv.command()
@click.argument("project_id")
@click.option("--title", "-t", default=None)
def create(project_id: str, title: str | None):
    app = Lemoria()
    pid = _resolve_id(app.session, Project, project_id) or project_id
    c = app.memory.create_conversation(pid, title)
    click.echo(f"Conversation [{c.id}] created.")


@conv.command()
@click.argument("conversation_id")
@click.argument("role")
@click.argument("content")
def add(conversation_id: str, role: str, content: str):
    app = Lemoria()
    cid = _resolve_id(app.session, Conversation, conversation_id) or conversation_id
    m = app.memory.add_message(cid, role, content)
    click.echo(f"Message added (id={m.id}).")


@conv.command()
@click.argument("project_id")
def list(project_id: str):
    app = Lemoria()
    pid = _resolve_id(app.session, Project, project_id) or project_id
    for c in app.memory.list_conversations(pid):
        click.echo(f"  {c.id}  {c.title or '(no title)'}  [{c.created_at}]")


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
    click.echo(f"Agent [{a.id}] {a.name} registered.")


@agent.command()
def list():
    app = Lemoria()
    for a in app.orchestrator.list_agents():
        click.echo(f"  {a.id}  {a.name} ({a.role})")


@cli.group()
def flow():
    """SDD workflow."""


@flow.command()
@click.argument("project_id")
@click.argument("idea")
def start(project_id: str, idea: str):
    app = Lemoria()
    pid = _resolve_id(app.session, Project, project_id) or project_id
    prd = app.flow.start_flow(pid, idea)
    click.echo(f"Flow started. PRD [{prd.id}] created.")


@flow.command()
@click.argument("prd_id")
def advance(prd_id: str):
    app = Lemoria()
    pid = _resolve_id(app.session, PRD, prd_id) or prd_id
    app.flow.advance(pid)
    click.echo(f"PRD {pid} advanced to active.")


@flow.command()
@click.argument("prd_id")
def complete(prd_id: str):
    app = Lemoria()
    pid = _resolve_id(app.session, PRD, prd_id) or prd_id
    app.flow.complete(pid)
    click.echo(f"PRD {pid} completed.")


@flow.command()
@click.argument("project_id")
@click.option("--status", "-s", default=None, help="Filter by status")
def list(project_id: str, status: str | None):
    app = Lemoria()
    pid = _resolve_id(app.session, Project, project_id) or project_id
    query = app.session.query(PRD).filter(PRD.project_id == pid)
    if status:
        query = query.filter(PRD.status == status)
    for p in query.order_by(PRD.created_at.desc()).all():
        click.echo(f"  {p.id}  [{p.status:10}]  {p.title[:60]}")


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
    pid = _resolve_id(app.session, Project, project_id) or project_id
    prid = _resolve_id(app.session, PRD, prd_id) or prd_id
    t = app.flow.create_task(pid, prid, None, title, agent_id)
    if description:
        t.description = description
        app.session.commit()
    click.echo(f"Task [{t.id}] created: {title}")


@task.command()
@click.argument("project_id")
@click.option("--status", "-s", default=None, help="Filter by status")
def list(project_id: str, status: str | None):
    app = Lemoria()
    pid = _resolve_id(app.session, Project, project_id) or project_id
    query = app.session.query(Task).filter(Task.project_id == pid)
    if status:
        query = query.filter(Task.status == status)
    for t in query.order_by(Task.created_at).all():
        click.echo(f"  {t.id}  [{t.status:10}]  {t.title}")


@task.command()
@click.argument("task_id")
@click.argument("new_status")
def status(task_id: str, new_status: str):
    app = Lemoria()
    tid = _resolve_id(app.session, Task, task_id) or task_id
    t = app.session.get(Task, tid)
    if t:
        t.status = new_status
        app.session.commit()
        click.echo(f"Task {tid} → {new_status}")
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
    pid = _resolve_id(app.session, Project, project_id) or project_id
    d = app.flow.record_decision(pid, title, description, rationale)
    click.echo(f"Decision [{d.id}] logged: {title}")


@decision.command()
@click.argument("project_id")
def list(project_id: str):
    app = Lemoria()
    pid = _resolve_id(app.session, Project, project_id) or project_id
    for d in app.session.query(Decision).filter(Decision.project_id == pid).order_by(Decision.created_at.desc()).all():
        click.echo(f"  {d.id}  [{d.status:10}]  {d.title}")


@cli.group()
def vault():
    """Export project data to markdown vault."""


@vault.command()
@click.argument("project_id")
def sync(project_id: str):
    """Export all project data to the vault as markdown files."""
    app = Lemoria()
    pid = _resolve_id(app.session, Project, project_id) or project_id
    p = app.projects.get(pid)
    if not p:
        click.echo("Project not found.")
        return

    name = p.name
    count = {"prds": 0, "decisions": 0, "convs": 0}

    overview = f"# {p.name}\n\n**{p.description or 'No description'}**\n"
    app.vault.export_project_overview(name, overview)
    click.echo(f"  exported  projects/{name}/README.md")

    for prd in app.session.query(PRD).filter(PRD.project_id == pid).order_by(PRD.created_at).all():
        content = f"# PRD: {prd.title}\n\n**Status**: {prd.status}\n**Created**: {prd.created_at}\n\n{prd.content or ''}\n"
        app.vault.export_prd(name, prd.id[:8], content)
        count["prds"] += 1

    for d in app.session.query(Decision).filter(Decision.project_id == pid).order_by(Decision.created_at).all():
        app.vault.export_decision(name, d.id[:8], d.title, d.description or "", d.rationale, d.status)
        count["decisions"] += 1

    for c in app.session.query(Conversation).filter(Conversation.project_id == pid).order_by(Conversation.created_at).all():
        lines = [f"# Conversation: {c.title or 'Untitled'}\n", f"**Created**: {c.created_at}\n"]
        for m in c.messages:
            lines.append(f"## {m.role}\n\n{m.content}\n")
        app.vault.export_conversation(name, c.id[:8], "\n".join(lines))
        count["convs"] += 1

    from database.models.agent import Agent
    agents_data = [
        {"name": a.name, "role": a.role, "description": a.description}
        for a in app.session.query(Agent).order_by(Agent.created_at).all()
    ]
    app.vault.export_agents(name, agents_data)
    click.echo(f"  exported  projects/{name}/agents.md ({len(agents_data)} agents)")

    tasks_data = [
        {"title": t.title, "status": t.status, "description": t.description}
        for t in app.session.query(Task).filter(Task.project_id == pid).order_by(Task.created_at).all()
    ]
    app.vault.export_tasks(name, tasks_data)
    click.echo(f"  exported  projects/{name}/tasks.md ({len(tasks_data)} tasks)")

    from database.models.commit import Commit
    task_ids = [t.id for t in app.session.query(Task).filter(Task.project_id == pid).all()]
    commits = app.session.query(Commit)
    if task_ids:
        commits = commits.filter((Commit.task_id.in_(task_ids)) | (Commit.task_id.is_(None)))
    commits_data = [
        {"sha": c.sha, "message": c.message, "author": c.author}
        for c in commits.order_by(Commit.created_at).all()
    ]
    app.vault.export_commits(name, commits_data)
    click.echo(f"  exported  projects/{name}/commits.md ({len(commits_data)} commits)")

    click.echo(f"\nVault sync complete: {count['prds']} PRDs, {count['decisions']} decisions, {count['convs']} conversations.")
    app.close()


if __name__ == "__main__":
    cli()