from pathlib import Path

import click

from database.models.conversation import Conversation
from database.models.decision import Decision
from database.models.flow_step import FlowStep
from database.models.prd import PRD
from database.models.project import Project
from database.models.task import Task

from .agents import AgentSync
from .config import settings
from .core import Lemoria


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
@click.version_option(package_name="lemoria", prog_name="lemoria")
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


@project.command("list")
def list_cmd():
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


@conv.command("list")
@click.argument("project_id")
def list_cmd(project_id: str):
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


@agent.command("list")
def list_cmd():
    app = Lemoria()
    for a in app.orchestrator.list_agents():
        click.echo(f"  {a.id}  {a.name} ({a.role})")


def _syncer(app, agents_dir: str | None) -> AgentSync:
    directory = Path(agents_dir).expanduser() if agents_dir else settings.opencode_agents_dir
    return AgentSync(app.session, directory)


@agent.command("sync")
@click.option("--dry-run", is_flag=True, default=False, help="Report what would change, write nothing")
@click.option("--dir", "agents_dir", default=None, help="Override the agents directory")
def sync_cmd(dry_run: bool, agents_dir: str | None):
    """Mirror .opencode/agents/*.md into the database."""
    app = Lemoria()
    syncer = _syncer(app, agents_dir)
    if not syncer.agents_dir.is_dir():
        click.echo(f"Error: no agents directory at {syncer.agents_dir}", err=True)
        app.close()
        raise SystemExit(1)

    report = syncer.sync(dry_run=dry_run)
    verb = "would sync" if dry_run else "synced"
    total = sum(len(v) for v in report.values())
    click.echo(f"{verb} {total} agent(s) from {syncer.agents_dir}")
    for key in ("created", "updated", "deactivated", "unchanged"):
        names = report[key]
        if names:
            click.echo(f"  {key:11} {len(names)}  {', '.join(names)}")
    if not total:
        click.echo("  nothing to do")
    app.close()


@agent.command("status")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit JSON instead of a table")
def status_cmd(as_json: bool):
    """Show each agent's model, live sessions and token usage.

    The Omarchy panel models a provider, not a subagent, so this is where the
    per-agent breakdown lives.
    """
    import json as _json

    from database.models.agent import Agent

    from .opencode_telemetry import OpenCodeTelemetry

    app = Lemoria()
    agents = {a.name: a for a in app.session.query(Agent).order_by(Agent.name).all()}
    telemetry = OpenCodeTelemetry().read()
    orchestrator_model = None
    root = telemetry.by_agent.get("orchestrator")
    if root:
        orchestrator_model = root.model

    if as_json:
        payload = {
            "telemetryAvailable": telemetry.available,
            "telemetryReason": telemetry.reason,
            "orchestratorModel": orchestrator_model,
            "agents": [
                {
                    "name": name,
                    # False for opencode's own builtins: they show up in
                    # telemetry but have no .md, so there is nothing to pin.
                    "managed": agent is not None,
                    "role": agent.role if agent else None,
                    "mode": agent.config_dict.get("mode") if agent else None,
                    "model": agent.model if agent else None,
                    "variant": agent.variant if agent else None,
                    "inheritsFrom": None if (agent is None or agent.model) else orchestrator_model,
                    "sessions": usage.sessions if usage else 0,
                    "subagentSessions": usage.subagent_sessions if usage else 0,
                    "activeSessions": usage.active_sessions if usage else 0,
                    "tokens": usage.tokens if usage else 0,
                    "cost": usage.cost if usage else 0.0,
                    "observedModel": usage.model if usage else None,
                    "observedVariant": usage.variant if usage else None,
                }
                for name, agent, usage in (
                    (name, agents.get(name), telemetry.by_agent.get(name))
                    for name in sorted(set(agents) | set(telemetry.by_agent))
                )
            ],
        }
        click.echo(_json.dumps(payload, indent=2))
        app.close()
        return

    def human(value: int) -> str:
        for unit, size in (("G", 1_000_000_000), ("M", 1_000_000), ("K", 1_000)):
            if abs(value) >= size:
                return f"{value / size:.1f}{unit}"
        return str(value)

    def short(model: str | None) -> str:
        return (model or "?").rstrip("/").split("/")[-1]

    header = f"{'agent':22} {'source':8} {'model':16} {'variant':8} {'sess':>5} {'live':>5} {'tokens':>9}"
    click.echo(header)
    click.echo("-" * len(header))

    # DB-registered agents first: those are the ones Lemoria manages and can
    # pin a model on. opencode's own builtins follow, since they appear in
    # telemetry but have no .md to configure.
    managed = sorted(agents)
    builtins = sorted(set(telemetry.by_agent) - set(agents))

    def render(name: str, is_managed: bool) -> None:
        agent, usage = agents.get(name), telemetry.by_agent.get(name)
        if agent and agent.model:
            model, source, variant = short(agent.model), "pinned", agent.variant or "default"
        else:
            model, source = short(orchestrator_model) or "?", "inherits"
            variant = (usage.variant if usage else None) or "default"
        if not is_managed:
            source = "builtin"
        live = usage.active_sessions if usage else 0
        click.echo(
            f"{name:22} {source:8} {model:16} {variant:8} "
            f"{(usage.sessions if usage else 0):>5} "
            f"{str(live) + ('*' if live else ''):>5} "
            f"{human(usage.tokens if usage else 0):>9}"
        )

    for name in managed:
        render(name, True)
    if managed and builtins:
        click.echo("-" * len(header))
    for name in builtins:
        render(name, False)

    if not telemetry.available:
        click.echo(f"\n! opencode telemetry unavailable: {telemetry.reason}", err=True)
    click.echo("\ninherits = no model in frontmatter, so opencode uses the calling agent's")
    click.echo("builtin   = opencode's own agent, no .md to pin a model on")
    click.echo("*         = session updated in the last 5 minutes")
    app.close()


@agent.command("model")
@click.argument("name")
@click.argument("model", required=False)
@click.option("--variant", "-v", default=None, help="Reasoning effort variant, e.g. high or low")
@click.option("--clear", is_flag=True, default=False, help="Remove the pin and inherit the caller's model")
def model_cmd(name: str, model: str | None, variant: str | None, clear: bool):
    """Show or set the model an agent runs on.

    With no MODEL, prints the current one. Passing MODEL writes it into the
    agent's markdown. Use --clear to remove the pin and restore inheritance
    from the invoking agent.
    """
    if clear and model:
        raise click.UsageError("--clear and MODEL are mutually exclusive")
    if clear:
        model, variant = None, None
    app = Lemoria()
    syncer = _syncer(app, None)
    path = syncer.agents_dir / f"{name}.md"
    if not path.is_file():
        click.echo(f"Error: no agent file at {path}", err=True)
        app.close()
        raise SystemExit(1)

    # `clear` also normalises both to None, so it must not fall through to the
    # read branch below.
    if model is None and variant is None and not clear:
        current = next((d for d in syncer.discover() if d.name == name), None)
        if current is None:
            click.echo(f"Error: cannot parse {path}", err=True)
            app.close()
            raise SystemExit(1)
        if current.model:
            click.echo(f"{name}: model={current.model} variant={current.variant or 'default'}")
        else:
            click.echo(f"{name}: inherited (no model in frontmatter)")
        app.close()
        return

    try:
        definition = syncer.set_model(name, model, variant)
        syncer.sync()
    except (ValueError, FileNotFoundError) as error:
        click.echo(f"Error: {error}", err=True)
        app.close()
        raise SystemExit(1)

    if definition.model:
        click.echo(f"{name}: model={definition.model} variant={definition.variant or 'default'}")
    else:
        click.echo(f"{name}: no model pinned; opencode will inherit the caller's")
    click.echo(f"  updated {definition.path}")
    app.close()


@cli.command("usage")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit JSON instead of a table")
def usage_cmd(as_json: bool):
    """Show opencode token usage: all-time total, by model, by agent, last 7 days.

    Everything the Omarchy panel draws, plus the per-agent and cost breakdown
    the panel's contract has no field for. On a machine without Omarchy this
    is the whole view.
    """
    import json as _json

    from .opencode_telemetry import OpenCodeTelemetry

    telemetry = OpenCodeTelemetry().read()
    if not telemetry.available:
        if as_json:
            click.echo(_json.dumps({"available": False, "reason": telemetry.reason}, indent=2))
        else:
            click.echo(f"No telemetry: {telemetry.reason}", err=True)
        # Non-zero: the command was asked for numbers and could not produce
        # any, which is a failure worth catching in a script.
        raise SystemExit(1)

    def human(count: int) -> str:
        """Token counts reach hundreds of millions; digits stop being readable."""
        for unit, size in (("G", 1_000_000_000), ("M", 1_000_000), ("K", 1_000)):
            if count >= size:
                return f"{count / size:.1f}{unit}"
        return str(count)

    if as_json:
        click.echo(_json.dumps({
            "available": True,
            "total": {
                "tokens": telemetry.total_tokens,
                "sessions": telemetry.total_sessions,
                "prompts": telemetry.total_prompts,
                "cost": telemetry.total_cost,
                "activeDays": len(telemetry.active_dates),
                "firstDay": telemetry.active_dates[0] if telemetry.active_dates else None,
                "lastDay": telemetry.active_dates[-1] if telemetry.active_dates else None,
            },
            "today": {
                "tokens": telemetry.today_tokens,
                "sessions": telemetry.today_sessions,
                "prompts": telemetry.today_prompts,
            },
            "byModel": [
                {
                    "model": model,
                    "tokens": (
                        bucket.input_tokens + bucket.output_tokens
                        + bucket.cache_read + bucket.cache_write
                    ),
                    "inputTokens": bucket.input_tokens,
                    "outputTokens": bucket.output_tokens,
                    "cacheReadInputTokens": bucket.cache_read,
                    "reasoningTokens": bucket.reasoning,
                }
                for model, bucket in sorted(
                    telemetry.by_model.items(),
                    key=lambda kv: -(
                        kv[1].input_tokens + kv[1].output_tokens
                        + kv[1].cache_read + kv[1].cache_write
                    ),
                )
            ],
            "byAgent": [
                {
                    "agent": name,
                    "tokens": entry.tokens,
                    "sessions": entry.sessions,
                    "activeSessions": entry.active_sessions,
                    "cost": entry.cost,
                    "model": entry.model,
                }
                for name, entry in sorted(
                    telemetry.by_agent.items(), key=lambda kv: -kv[1].tokens
                )
            ],
            "recentDays": telemetry.recent_days,
        }, indent=2))
        return

    span = ""
    if telemetry.active_dates:
        span = f"  ({telemetry.active_dates[0]} → {telemetry.active_dates[-1]})"
    click.echo(f"\nTotal   {human(telemetry.total_tokens)} tokens{span}")
    click.echo(f"        {telemetry.total_sessions} sessions · {telemetry.total_prompts} prompts"
               f" · ${telemetry.total_cost:.2f} · {len(telemetry.active_dates)} active days")
    click.echo(f"Today   {human(telemetry.today_tokens)} tokens"
               f" · {telemetry.today_sessions} sessions · {telemetry.today_prompts} prompts\n")

    click.echo("By model (all-time)")
    for model, bucket in sorted(
        telemetry.by_model.items(),
        key=lambda kv: -(
            kv[1].input_tokens + kv[1].output_tokens
            + kv[1].cache_read + kv[1].cache_write
        ),
    ):
        total = bucket.input_tokens + bucket.output_tokens + bucket.cache_read + bucket.cache_write
        click.echo(f"  {model:44} {human(total):>9}  in {human(bucket.input_tokens):>8}"
                   f"  out {human(bucket.output_tokens):>7}  cache {human(bucket.cache_read):>8}")

    agents = [entry for entry in telemetry.by_agent.values() if entry.tokens]
    if agents:
        click.echo("\nBy agent (all-time)")
        for entry in sorted(agents, key=lambda e: -e.tokens):
            live = f"  {entry.active_sessions} live" if entry.active_sessions else ""
            click.echo(f"  {entry.name:24} {human(entry.tokens):>9}  "
                       f"{entry.sessions} sessions{live}")
    click.echo("")


@cli.group()
def omarchy():
    """Integrate with the Omarchy desktop shell."""


@omarchy.command("record")
@click.option("--output", "-o", default=None, help="Write here instead of the panel's directory")
@click.option("--print", "print_only", is_flag=True, default=False, help="Print the record, write nothing")
def omarchy_record(output: str | None, print_only: bool):
    """Publish opencode usage for the Omarchy agents panel."""
    from .omarchy import build_record, validate_record
    from .opencode_telemetry import OpenCodeTelemetry

    telemetry = OpenCodeTelemetry().read()
    record = build_record(telemetry)
    problems = validate_record(record)
    if problems:
        for problem in problems:
            click.echo(f"contract problem: {problem}", err=True)
    if print_only:
        import json as _json

        click.echo(_json.dumps(record, indent=2, sort_keys=True))
        return

    from .omarchy import write_record

    destination = write_record(record, Path(output) if output else None)
    click.echo(f"Wrote {destination}")
    if telemetry.reason:
        click.echo(f"  ! {telemetry.reason}", err=True)
    if record["ready"]:
        click.echo(
            f"  {record['totalSessions']} sessions, "
            f"{record['totalPrompts']} prompts, "
            f"{record['totalTokens']:,} tokens acumulados, "
            f"${record['totalCost']:.2f}"
        )
    else:
        click.echo("  record is not ready; the panel will not show a tab")


@omarchy.command("install")
@click.option("--interval", default="1min", help="How often the panel should refresh (e.g. 1min, 5min, 1h)")
@click.option("--enable", is_flag=True, default=True, help="Enable and start the timer (--no-enable to only write)")
def omarchy_install(interval: str, enable: bool):
    """Install the user-level timer that keeps the panel record fresh."""
    from .omarchy import install_timer, write_record

    service, timer = install_timer(interval=interval)
    click.echo(f"Wrote {service}")
    click.echo(f"Wrote {timer}")

    # Publish once now so the panel is populated before the first tick.
    from .omarchy import build_record
    from .opencode_telemetry import OpenCodeTelemetry

    destination = write_record(build_record(OpenCodeTelemetry().read()))
    click.echo(f"Wrote {destination}")

    if not enable:
        click.echo("\nTimer written but not enabled.")
        return

    import shutil as _shutil
    import subprocess

    if not _shutil.which("systemctl"):
        click.echo("\nsystemctl not found; enable the timer manually.", err=True)
        return
    try:
        # Stop before reloading, always. A daemon-reload under a running timer
        # can leave systemd holding a stale record of when the service last
        # exited, which makes the OnUnitActiveSec elapse compute to zero: the
        # timer then sits in "elapsed" forever, still reporting enabled and
        # never firing again. Stopping first drops that record. It costs
        # nothing when the timer was already stopped.
        subprocess.run(["systemctl", "--user", "stop", "lemoria-usage.timer"], check=False)
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "--user", "enable", "--now", "lemoria-usage.timer"], check=True)
    except subprocess.CalledProcessError as error:
        click.echo(f"\ncould not enable the timer: {error}", err=True)
        return

    # Verify the timer actually has a next run scheduled, rather than trusting
    # "enabled". A timer can report active with nothing queued, which looks
    # fine until you notice the record stopped updating.
    if not _timer_armed():
        subprocess.run(["systemctl", "--user", "start", "lemoria-usage.service"], check=False)
        if _timer_armed():
            click.echo("\nTimer was installed but not scheduled; re-armed it.")
        else:
            click.echo(
                "\n! The timer is enabled but has no next run scheduled. Try:\n"
                "    systemctl --user stop lemoria-usage.timer\n"
                "    systemctl --user start lemoria-usage.service\n"
                "    systemctl --user start lemoria-usage.timer",
                err=True,
            )
            return

    click.echo("\nTimer enabled. Next runs:")
    subprocess.run(
        ["systemctl", "--user", "list-timers", "lemoria-usage.timer", "--no-pager"],
        check=False,
    )


def _timer_armed() -> bool:
    """Whether systemd has a next elapse queued for the timer.

    SubState is the only reliable signal here. `list-timers` and the
    TimersMonotonic dump both keep reporting a next elapse for a stopped or
    broken timer, because they describe the persisted config rather than the
    live schedule. SubState does not:

      waiting  armed, fires on the next elapse
      dead     not started
      elapsed  the bug this guards against: unit is active, nothing is queued,
               and it never fires again
    """
    import shutil as _shutil
    import subprocess

    if not _shutil.which("systemctl"):
        return False
    out = subprocess.run(
        ["systemctl", "--user", "show", "lemoria-usage.timer", "-p", "SubState", "--value"],
        capture_output=True, text=True, check=False,
    ).stdout.strip()
    return out == "waiting"


@omarchy.command("uninstall")
@click.option("--keep-record", is_flag=True, default=False, help="Leave the record in place (the panel keeps its last tab)")
def omarchy_uninstall(keep_record: bool):
    """Remove the user-level timer and the record it published.

    Everything written lives under the user's own home: two systemd units and
    one JSON file. Nothing under /usr/share/omarchy is ever touched, so there
    is nothing for omarchy update to miss.
    """
    import shutil as _shutil
    import subprocess

    from .omarchy import default_record_dir, default_unit_dir

    units = [
        default_unit_dir() / "lemoria-usage.service",
        default_unit_dir() / "lemoria-usage.timer",
    ]

    if _shutil.which("systemctl"):
        # Stop first: deleting a unit that systemd still has loaded leaves a
        # timer running from an in-memory copy of the old file.
        subprocess.run(["systemctl", "--user", "disable", "--now", "lemoria-usage.timer"],
                       check=False, capture_output=True)
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False, capture_output=True)

    for unit in units:
        if unit.exists():
            unit.unlink()
            click.echo(f"Removed {unit}")
        else:
            click.echo(f"Not present: {unit}")

    record = default_record_dir() / "lemoria.json"
    if keep_record:
        click.echo(f"\nKept the record: {record}")
        click.echo("The panel will keep showing its last values until they age out.")
    elif record.exists():
        record.unlink()
        click.echo(f"Removed {record}")
    else:
        click.echo(f"Not present: {record}")

    click.echo("\nUninstalled. Reinstall with: lemoria omarchy install")


@omarchy.command("where")
def omarchy_where():
    """Show where the panel reads its records from."""
    from .omarchy import default_record_dir

    directory = default_record_dir()
    click.echo(f"records: {directory}")
    if directory.is_dir():
        for path in sorted(directory.glob("*.json")):
            click.echo(f"  {path.name:16} {path.stat().st_size:>7} bytes")


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


@flow.command("list")
@click.argument("project_id")
@click.option("--status", "-s", default=None, help="Filter by status")
def list_cmd(project_id: str, status: str | None):
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


@task.command("list")
@click.argument("project_id")
@click.option("--status", "-s", default=None, help="Filter by status")
def list_cmd(project_id: str, status: str | None):
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


@decision.command("list")
@click.argument("project_id")
def list_cmd(project_id: str):
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


@spec.command("list")
@click.argument("prd_id")
def list_cmd(prd_id: str):
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


@error.command("list")
@click.argument("project_id")
@click.option("--unresolved", "-u", is_flag=True, default=False, help="Show only unresolved")
def list_cmd(project_id: str, unresolved: bool):
    app = Lemoria()
    pid = _resolve_id(app.session, Project, project_id) or project_id
    from database.models.error_record import ErrorRecord
    query = app.session.query(ErrorRecord).filter(ErrorRecord.project_id == pid)
    if unresolved:
        query = query.filter(ErrorRecord.resolved.is_(False))
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


@context.command("set")
@click.argument("project_id")
@click.option("--key", "-k", required=True, help="Context key")
@click.option("--value", "-v", required=True, help="Context value")
@click.option("--level", "-l", default="global", help="Context level (global, project, task, agent)")
def set_cmd(project_id: str, key: str, value: str, level: str):
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
    for warning in app.vault.warnings:
        click.echo(f"  ! {warning}", err=True)
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
    for warning in app.vault.warnings:
        click.echo(f"  ! {warning}", err=True)
    app.close()


if __name__ == "__main__":
    cli()
