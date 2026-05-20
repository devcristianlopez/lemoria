import click
from .core import Lemoria


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
    click.echo(f"Conversation {c.id} created.")


@conv.command()
@click.argument("conversation_id")
@click.argument("role")
@click.argument("content")
def add(conversation_id: str, role: str, content: str):
    app = Lemoria()
    m = app.memory.add_message(conversation_id, role, content)
    click.echo(f"Message added (id={m.id[:8]}).")


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
    app = Lemoria()
    prd = app.flow.start_flow(project_id, idea)
    click.echo(f"Flow started. PRD {prd.id} created.")


if __name__ == "__main__":
    cli()
