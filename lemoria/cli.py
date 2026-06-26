import click
from .core import Lemoria
from database.models.task import Task
from database.models.project import Project
from database.models.conversation import Conversation
from database.models.prd import PRD
from database.models.decision import Decision
from database.models.flow_step import FlowStep
from database.enums import FlowStepStatus


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


@flow.command()
@click.argument("flow_id")
@click.argument("step_name")
@click.option("--status", "-s", default="completed", help="Step status: completed, failed, skipped")
@click.option("--output", "-o", default=None, help="Step summary output")
def step(flow_id: str, step_name: str, status: str, output: str | None):
    """Record a step in the flow state machine."""
    app = Lemoria()
    fid = _resolve_id(app.session, PRD, flow_id) or flow_id

    if status == "running":
        fs = app.flow.start_step(fid, step_name)
        click.echo(f"Step [{fs.id}] {step_name} started.")
    elif status == "completed":
        app.flow.complete_step(fid, step_name, output)
        click.echo(f"Step {step_name} completed.")
    elif status == "failed":
        app.flow.fail_step(fid, step_name, output or "Unknown error")
        click.echo(f"Step {step_name} failed.")
    else:
        click.echo(f"Unknown status: {status}")
    app.close()


@flow.command()
@click.argument("flow_id")
def status(flow_id: str):
    """Show the current status of a flow (all steps)."""
    app = Lemoria()
    fid = _resolve_id(app.session, PRD, flow_id) or flow_id
    info = app.flow.get_flow_status(fid)

    if not info["steps"]:
        click.echo("No steps recorded for this flow yet.")
        app.close()
        return

    click.echo(f"\nFlow: {fid}")
    click.echo(f"Completed: {'✓' if info['completed'] else '○'}")
    if info["current_step"]:
        click.echo(f"Current step: {info['current_step']}")
    click.echo("")
    click.echo(f"  {'STEP':25} {'STATUS':15} {'OUTPUT'}")
    click.echo(f"  {'-'*25} {'-'*15} {'-'*30}")
    for s in info["steps"]:
        out = (s["output"] or "")[:40]
        click.echo(f"  {s['step']:25} {s['status']:15} {out}")
    click.echo("")
    app.close()


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
    """Update task status (pending, in_progress, completed, failed, cancelled)."""
    app = Lemoria()
    tid = _resolve_id(app.session, Task, task_id) or task_id
    t = app.flow.set_task_status(tid, new_status)
    if t:
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
def spec():
    """Manage specifications."""


@spec.command()
@click.argument("prd_id")
@click.option("--title", "-t", required=True, help="Spec title")
@click.option("--content", "-c", required=True, help="Spec content")
@click.option("--order", "-o", default=0, help="Order within PRD")
def create(prd_id: str, title: str, content: str, order: int):
    app = Lemoria()
    prid = _resolve_id(app.session, PRD, prd_id) or prd_id
    s = app.flow.add_spec(prid, title, content, order)
    click.echo(f"Spec [{s.id}] created: {title}")
    app.close()


@spec.command()
@click.argument("prd_id")
def list(prd_id: str):
    app = Lemoria()
    prid = _resolve_id(app.session, PRD, prd_id) or prd_id
    from database.models.spec import Spec
    for s in app.session.query(Spec).filter(Spec.prd_id == prid).order_by(Spec.order).all():
        click.echo(f"  {s.id}  [{s.status:12}]  {s.title}")
    app.close()


@cli.group()
def error():
    """Manage errors and solutions."""


@error.command()
@click.argument("project_id")
@click.option("--source", default=None, help="Error source (e.g., 'api', 'cli')")
@click.option("--type", "error_type", default=None, help="Error type")
@click.option("--message", "-m", required=True, help="Error message")
def log(project_id: str, source: str | None, error_type: str | None, message: str):
    app = Lemoria()
    pid = _resolve_id(app.session, Project, project_id) or project_id
    from database.models.error_record import ErrorRecord
    e = ErrorRecord(project_id=pid, source=source, error_type=error_type, message=message)
    app.session.add(e)
    app.session.commit()
    click.echo(f"Error [{e.id}] logged.")
    app.close()


@error.command()
@click.argument("project_id")
@click.option("--unresolved", "-u", is_flag=True, default=False, help="Show only unresolved")
def list(project_id: str, unresolved: bool):
    app = Lemoria()
    pid = _resolve_id(app.session, Project, project_id) or project_id
    from database.models.error_record import ErrorRecord
    query = app.session.query(ErrorRecord).filter(ErrorRecord.project_id == pid)
    if unresolved:
        query = query.filter(ErrorRecord.resolved == False)
    for e in query.order_by(ErrorRecord.created_at.desc()).all():
        marker = "✓" if e.resolved else "✗"
        click.echo(f"  {marker} {e.id}  {e.error_type or '?'}: {e.message[:60]}")
    app.close()


@error.command()
@click.argument("error_id")
def resolve(error_id: str):
    app = Lemoria()
    from database.models.error_record import ErrorRecord
    eid = _resolve_id(app.session, ErrorRecord, error_id) or error_id
    e = app.session.get(ErrorRecord, eid)
    if e:
        e.resolved = True
        app.session.commit()
        click.echo(f"Error {eid} resolved.")
    else:
        click.echo("Error not found.")
    app.close()


@cli.group()
def context():
    """Manage hierarchical context."""


@context.command()
@click.argument("project_id")
@click.option("--key", "-k", required=True, help="Context key")
@click.option("--value", "-v", required=True, help="Context value")
@click.option("--level", "-l", default="global", help="Context level (global, project, task, agent)")
def set(project_id: str, key: str, value: str, level: str):
    app = Lemoria()
    pid = _resolve_id(app.session, Project, project_id) or project_id
    from database.models.context import Context
    ctx = Context(project_id=pid, key=key, value=value, level=level)
    app.session.add(ctx)
    app.session.commit()
    click.echo(f"Context {key}={value} ({level}) set.")
    app.close()


@context.command()
@click.argument("project_id")
@click.option("--key", "-k", required=True, help="Context key")
def get(project_id: str, key: str):
    app = Lemoria()
    pid = _resolve_id(app.session, Project, project_id) or project_id
    from database.models.context import Context
    ctx = app.session.query(Context).filter(Context.project_id == pid, Context.key == key).order_by(Context.created_at.desc()).first()
    if ctx:
        click.echo(f"{ctx.key} = {ctx.value}  [{ctx.level}]")
    else:
        click.echo(f"No context found for key '{key}'.")
    app.close()

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

    # --- Consultar datos relacionados ---
    prds = app.session.query(PRD).filter(PRD.project_id == pid).order_by(PRD.created_at).all()
    decisions = app.session.query(Decision).filter(Decision.project_id == pid).order_by(Decision.created_at).all()
    conversations = app.session.query(Conversation).filter(Conversation.project_id == pid).order_by(Conversation.created_at).all()

    from database.models.agent import Agent
    agents_data = [
        {"name": a.name, "role": a.role, "description": a.description}
        for a in app.session.query(Agent).order_by(Agent.created_at).all()
    ]
    tasks = app.session.query(Task).filter(Task.project_id == pid).order_by(Task.created_at).all()
    tasks_data = [
        {"title": t.title, "status": t.status, "description": t.description}
        for t in tasks
    ]
    from database.models.commit import Commit
    task_ids = [t.id for t in tasks]
    commits_query = app.session.query(Commit)
    if task_ids:
        commits_query = commits_query.filter((Commit.task_id.in_(task_ids)) | (Commit.task_id.is_(None)))
    commits = commits_query.order_by(Commit.created_at).all()
    commits_data = [
        {"sha": c.sha, "message": c.message, "author": c.author}
        for c in commits
    ]

    # --- Flow steps ---
    flow_steps = app.session.query(FlowStep).filter(FlowStep.flow_id.in_([prd.id for prd in prds])).order_by(FlowStep.created_at).all() if prds else []

    # Export flow steps per PRD
    if flow_steps:
        for prd in prds:
            prd_steps = [s for s in flow_steps if s.flow_id == prd.id]
            if prd_steps:
                app.vault.export_flow_steps(name, prd.title, prd_steps)

    # --- README (overview) ---
    overview_parts = [f"# {p.name}\n\n**{p.description or 'No description'}**\n"]

    if prds:
        overview_parts.append("\n## 📋 PRDs\n")
        for prd in prds:
            link = app.vault.entity_wikilink(name, "prd", prd.id[:8], prd.title[:60])
            overview_parts.append(f"- {link} — `{prd.status}`\n")

    if decisions:
        overview_parts.append("\n## 📐 Decisiones (ADR)\n")
        for d in decisions:
            link = app.vault.entity_wikilink(name, "decision", d.id[:8], d.title)
            overview_parts.append(f"- {link} — `{d.status}`\n")

    if flow_steps:
        overview_parts.append("\n## 🔄 Flow Steps\n")
        steps_by_status = {}
        for s in flow_steps:
            steps_by_status.setdefault(s.status, 0)
            steps_by_status[s.status] += 1
        for status, num in steps_by_status.items():
            overview_parts.append(f"- {status}: {num}\n")

    if conversations:
        overview_parts.append("\n## 💬 Conversaciones\n")
        for c in conversations:
            link = app.vault.entity_wikilink(name, "conversation", c.id[:8], c.title or "Sin título")
            overview_parts.append(f"- {link}\n")

    tasks_link = app.vault.wikilink(app.vault.entity_path(name, "tasks"), "Tasks")
    commits_link = app.vault.wikilink(app.vault.entity_path(name, "commits"), "Commits")
    agents_link = app.vault.wikilink(app.vault.entity_path(name, "agents"), "Agents")
    overview_parts.append(f"\n---\n[ {tasks_link} · {commits_link} · {agents_link} ]\n")

    app.vault.export_project_overview(name, "".join(overview_parts))
    click.echo(f"  exported  projects/{name}/README.md")

    # --- PRDs ---
    for prd in prds:
        project_link = app.vault.project_wikilink(name)
        tasks_link_local = app.vault.wikilink(app.vault.entity_path(name, "tasks"), "Tasks")
        prd_tasks = [t for t in tasks if t.prd_id == prd.id]
        content_parts = [
            f"# PRD: {prd.title}\n",
            f"**Proyecto**: {project_link}\n",
            f"**Status**: {prd.status}\n",
            f"**Created**: {prd.created_at}\n\n",
            f"{prd.content or ''}\n",
        ]
        if prd_tasks:
            content_parts.append("\n### Tareas relacionadas\n")
            for t in prd_tasks:
                content_parts.append(f"- **{t.title}** [{t.status}]\n")
        # Flow steps within this PRD
        prd_steps = [s for s in flow_steps if s.flow_id == prd.id]
        if prd_steps:
            content_parts.append("\n### Flow steps\n")
            for s in prd_steps:
                content_parts.append(f"- `{s.step}` → {s.status}\n")
        content_parts.append(f"\n---\nVolver a {project_link} · {tasks_link_local}\n")
        app.vault.export_prd(name, prd.id[:8], "".join(content_parts))
        count["prds"] += 1

    # --- Decisiones (ADR) ---
    for d in decisions:
        app.vault.export_decision(name, d.id[:8], d.title, d.description or "", d.rationale, d.status)
        count["decisions"] += 1

    # --- Conversaciones ---
    for c in conversations:
        project_link = app.vault.project_wikilink(name)
        conv_parts = [
            f"# Conversación: {c.title or 'Untitled'}\n",
            f"**Proyecto**: {project_link}\n",
            f"**Created**: {c.created_at}\n\n",
        ]
        for m in c.messages:
            conv_parts.append(f"## {m.role}\n\n{m.content}\n")
        conv_parts.append(f"\n---\nVolver a {project_link}\n")
        app.vault.export_conversation(name, c.id[:8], "".join(conv_parts))
        count["convs"] += 1

    # --- Agents ---
    app.vault.export_agents(name, agents_data)
    click.echo(f"  exported  projects/{name}/agents.md ({len(agents_data)} agents)")

    # --- Tasks ---
    app.vault.export_tasks(name, tasks_data)
    click.echo(f"  exported  projects/{name}/tasks.md ({len(tasks_data)} tasks)")

    # --- Commits ---
    app.vault.export_commits(name, commits_data)
    click.echo(f"  exported  projects/{name}/commits.md ({len(commits_data)} commits)")

    click.echo(f"\nVault sync complete: {count['prds']} PRDs, {count['decisions']} decisions, {count['convs']} conversations.")
    app.close()


@vault.command()
@click.argument("project_id")
@click.option("--name", default=None, help="Override project name in vault path")
def restore(project_id: str, name: str | None):
    """Restore project data from vault markdown files back to the database."""
    app = Lemoria()
    pid = _resolve_id(app.session, Project, project_id) or project_id
    p = app.projects.get(pid)
    if not p:
        click.echo("Project not found in DB. Create it first: lemoria project create <name>")
        app.close()
        return

    project_name = name or p.name
    restored = app.restore_from_vault(pid, project_name)
    click.echo(f"Restored: {restored['decisions']} decisions, {restored['flow_steps']} flow steps")
    app.close()


if __name__ == "__main__":
    cli()
