"""Publish Lemoria's opencode usage to Lemoria's own Omarchy plugin.

The native Omarchy agents panel owns
``$XDG_STATE_HOME/omarchy/agents/usage/*.json`` for Claude/Codex/Fireworks. Do
not write Lemoria there: adding a record to that directory adds a provider to
the native panel and can perturb tabs the user did not ask us to touch.

Lemoria writes a private record to
``$XDG_STATE_HOME/lemoria/omarchy/usage.json``. The bundled user plugin
``lemoria.usage`` watches that file and draws the all-time total, monthly
budget, seven-day history and per-agent model table.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from .budget import Budget
from .opencode_telemetry import OpenCodeTelemetry, Telemetry

AGENT_ID = "lemoria"
AGENT_NAME = "Lemoria"
SCHEMA_VERSION = 1

REQUIRED_KEYS = (
    "schemaVersion", "id", "name", "updatedAt", "ready", "hasLocalStats",
    "todayPrompts", "todaySessions", "todayTotalTokens", "todayTokensByModel",
    "recentDays", "totalPrompts", "totalSessions", "activeDays", "activeDates",
    "modelUsage", "limits", "tierLabel",
)


def default_record_dir() -> Path:
    """Private state read by the Lemoria-owned Omarchy plugin.

    Do not write under ``omarchy/agents/usage`` here. That directory belongs to
    Omarchy's native agents panel (Claude/Codex/Fireworks). Putting Lemoria's
    record there adds a provider to that panel and can perturb tabs that we
    promised not to touch.
    """
    state_home = os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state")
    return Path(state_home) / "lemoria" / "omarchy"


def default_record_path() -> Path:
    return default_record_dir() / "usage.json"


def legacy_agents_record_path() -> Path:
    """Old path that made Lemoria appear inside Omarchy's native Agents panel."""
    state_home = os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state")
    return Path(state_home) / "omarchy" / "agents" / "usage" / f"{AGENT_ID}.json"


def remove_legacy_agents_record() -> bool:
    legacy = legacy_agents_record_path()
    if legacy.exists():
        legacy.unlink()
        return True
    return False


def native_agents_usage_dir() -> Path:
    """The native Omarchy Agents panel directory. Read/patch with care."""
    state_home = os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state")
    return Path(state_home) / "omarchy" / "agents" / "usage"


def native_codex_record_path() -> Path:
    return native_agents_usage_dir() / "codex.json"


def codex_limits_cache_path() -> Path:
    return default_record_dir() / "codex-limits.json"


def _read_json(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _write_json_atomic(path: Path, payload: dict, mode: int = 0o600) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    temp_path = Path(temp_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, separators=(",", ":"), sort_keys=True)
            stream.write("\n")
        temp_path.chmod(mode)
        temp_path.replace(path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise
    return path


def _codex_int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _codex_has_usage(record: dict) -> bool:
    return bool(record.get("ready")) and (
        _codex_int(record.get("todayTotalTokens")) > 0
        or _codex_int(record.get("totalPrompts")) > 0
        or _codex_int(record.get("todayPrompts")) > 0
    )


def _codex_good_limits(record: dict) -> bool:
    return (
        isinstance(record.get("limits"), list)
        and len(record["limits"]) > 0
        and not str(record.get("usageStatusText") or "")
    )


def stabilize_codex_record(
    record_path: Path | None = None,
    cache_path: Path | None = None,
) -> tuple[bool, str]:
    """Hide Codex collector's intermittent `account/read` failure from the panel.

    The native collector sometimes times out on the app-server RPC method
    `account/read`. When that happens it writes `authHelpText: "account/read"`,
    and the native panel flashes that implementation detail instead of usage. We
    do not edit `/usr/share/omarchy`; we only sanitize the user-state JSON and
    keep the last good limits/tier as a cache.
    """
    target = record_path or native_codex_record_path()
    cache = cache_path or codex_limits_cache_path()
    record = _read_json(target)
    if record is None:
        return False, "codex record missing"

    changed = False
    if _codex_good_limits(record):
        cached = _read_json(cache) or {}
        if (cached.get("limits"), cached.get("tierLabel")) != (
            record.get("limits") or [],
            record.get("tierLabel") or "",
        ):
            _write_json_atomic(cache, {
                "schemaVersion": 1,
                "updatedAt": datetime.now(UTC).isoformat(),
                "limits": record.get("limits") or [],
                "tierLabel": record.get("tierLabel") or "",
            })

    usage_status = str(record.get("usageStatusText") or "")
    auth_help = str(record.get("authHelpText") or "")
    has_usage = _codex_has_usage(record)

    if usage_status == "Codex limits unavailable":
        cached = _read_json(cache) or {}
        if cached.get("limits"):
            record["limits"] = cached["limits"]
            record["tierLabel"] = cached.get("tierLabel") or record.get("tierLabel") or ""
            record["usageStatusText"] = ""
            changed = True

    # These messages are auth/debug details, not useful usage data. When local
    # usage exists, the panel should keep showing usage rather than flashing an
    # RPC method name or a stale login hint.
    if has_usage and auth_help in {"account/read", "Run `codex login` to authenticate."}:
        record["authHelpText"] = ""
        changed = True

    if changed:
        _write_json_atomic(target, record)
        return True, "codex record stabilized"
    return False, "codex record already stable"


def default_plugin_dir() -> Path:
    """Where Omarchy's plugin catalog looks for user plugins."""
    return Path.home() / ".config" / "omarchy" / "plugins"


def plugin_source_dir() -> Path:
    """The bundled QML plugin shipped with Lemoria."""
    return Path(__file__).resolve().parent / "omarchy_plugin" / "lemoria.usage"


def plugin_destination_dir() -> Path:
    return default_plugin_dir() / "lemoria.usage"


def install_plugin(destination: Path | None = None) -> Path:
    """Install/update the user-level Omarchy plugin.

    Omarchy's catalog walks ~/.config/omarchy/plugins and treats every
    manifest.json at depth two as a first-class plugin. Copying there is the
    supported extension point; nothing under /usr/share/omarchy is touched.
    """
    source = plugin_source_dir()
    if not source.exists():
        raise FileNotFoundError(f"bundled plugin not found: {source}")
    target = destination or plugin_destination_dir()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    return target


def uninstall_plugin(destination: Path | None = None) -> bool:
    target = destination or plugin_destination_dir()
    if target.exists():
        shutil.rmtree(target)
        return True
    return False


# "No budget set" is what every existing caller means, and `NO_BUDGET` is
# frozen, so handing it out as a default is safe.
NO_BUDGET = Budget()


def build_record(telemetry: Telemetry, budget: Budget = NO_BUDGET) -> dict:
    """Turn a Telemetry snapshot into the panel's record.

    ``ready`` is what makes the panel show a tab at all, and the panel hides a
    provider with nothing to say -- so it is driven by real recorded usage
    rather than merely by the database being readable.
    """
    has_usage = telemetry.available and (
        telemetry.total_sessions > 0 or telemetry.total_tokens > 0
    )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "id": AGENT_ID,
        "name": AGENT_NAME,
        "updatedAt": datetime.now(UTC).isoformat(),
        "ready": has_usage,
        "hasLocalStats": telemetry.available,
        "hasPromptStats": telemetry.available,
        "tierLabel": "",
        "usageStatusText": "" if telemetry.available else "opencode data unavailable",
        "authHelpText": telemetry.reason,
        "limits": [],
        # The budget meter. `balance` is the pair the panel's own meter reads;
        # `budget` is the same answer with the detail a bar cannot show, and is
        # what our own panel draws. Both are null when no budget is set, and
        # neither invents a number.
        "balance": budget.as_contract(telemetry.month_tokens),
        "budget": budget.state(telemetry.month_tokens),
        # Device-scoped: this is one machine's opencode history, and the panel
        # sums device-scoped records across synced machines.
        "scope": "device",
        "todayPrompts": telemetry.today_prompts,
        "todaySessions": telemetry.today_sessions,
        "todayTotalTokens": telemetry.today_tokens,
        "todayTokensByModel": telemetry.today_by_model,
        "recentDays": telemetry.recent_days,
        "totalPrompts": telemetry.total_prompts,
        "totalSessions": telemetry.total_sessions,
        "activeDays": len(telemetry.active_dates),
        "activeDates": telemetry.active_dates,
        "modelUsage": {
            model: bucket.as_contract() for model, bucket in telemetry.by_model.items()
        },
        # Per agent, heaviest first. Not in the panel's contract either, and
        # this is the reason our own panel exists: there is nowhere in
        # `omarchy.agents` to show which model an agent runs on, so the answer
        # had no way to be displayed at all.
        "agents": [
            {
                "agent": entry.name,
                "tokens": entry.tokens,
                "todayTokens": entry.today_tokens,
                "prompts": entry.prompts,
                "todayPrompts": entry.today_prompts,
                "sessions": entry.sessions,
                "activeSessions": entry.active_sessions,
                "cost": entry.cost,
                "model": entry.model,
                "variant": entry.variant,
                "models": entry.models,
            }
            for entry in sorted(
                telemetry.by_agent.values(), key=lambda e: -e.tokens
            )
            if entry.tokens or entry.sessions or entry.prompts
        ],
        # Not part of the panel's contract: the panel ignores unknown keys, but
        # they make the record self-describing for anything else that reads it.
        "totalTokens": telemetry.total_tokens,
        "monthTokens": telemetry.month_tokens,
        "totalCost": telemetry.total_cost,
    }


def validate_record(record: dict) -> list[str]:
    """Return the contract keys that are missing or wrongly typed.

    The panel is a QML consumer: a missing field surfaces as an undefined
    property rather than a visible error, so this is worth checking.
    """
    problems = []
    numeric = (
        "todayPrompts", "todaySessions", "todayTotalTokens", "totalPrompts",
        "totalSessions", "activeDays", "schemaVersion",
    )
    for key in REQUIRED_KEYS:
        if key not in record:
            problems.append(f"missing: {key}")
    for key in numeric:
        if key in record and not isinstance(record[key], int):
            problems.append(f"{key} must be an int, got {type(record[key]).__name__}")
    if not isinstance(record.get("recentDays"), list):
        problems.append("recentDays must be a list")
    elif len(record["recentDays"]) != 7:
        problems.append(f"recentDays must hold 7 entries, got {len(record['recentDays'])}")
    if not isinstance(record.get("modelUsage"), dict):
        problems.append("modelUsage must be an object")
    for model, bucket in (record.get("modelUsage") or {}).items():
        for field_name in ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens"):
            if not isinstance(bucket.get(field_name), int):
                problems.append(f"modelUsage[{model}].{field_name} must be an int")
    return problems


def write_record(record: dict, output: Path | None = None) -> Path:
    """Write the record atomically.

    The panel watches this directory and re-reads on any change, so a partial
    file would show up as a broken tab. A temp file in the same directory plus
    rename gives the watcher a complete document every time.
    """
    destination = output or default_record_path()
    destination.parent.mkdir(parents=True, exist_ok=True)

    handle, temp_name = tempfile.mkstemp(
        dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp"
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(record, stream, separators=(",", ":"), sort_keys=True)
            stream.write("\n")
        # 600, matching the permissions Omarchy's own collectors write. The
        # record only carries token counts, but there is no reason for it to
        # be more permissive than the files next to it.
        temp_path.chmod(0o600)
        temp_path.replace(destination)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise
    return destination


def publish(db_path: Path | str | None = None, output: Path | str | None = None) -> tuple[Path, dict]:
    from .budget import Budget

    telemetry = OpenCodeTelemetry(db_path).read()
    record = build_record(telemetry, Budget.load())
    return write_record(record, Path(output) if output else None), record


SERVICE_UNIT = """[Unit]
Description=Publish lemoria opencode usage to the Lemoria Omarchy plugin

[Service]
Type=oneshot
ExecStart={executable} omarchy record
"""

TIMER_UNIT = """[Unit]
Description=Refresh the Lemoria usage widget

[Timer]
OnBootSec=1min
OnUnitActiveSec=1min
Persistent=true
Unit=lemoria-usage.service

[Install]
WantedBy=timers.target
"""

CODEX_STABILIZE_SERVICE_UNIT = """[Unit]
Description=Stabilize Omarchy Codex usage record

[Service]
Type=oneshot
ExecStart={executable} omarchy stabilize-codex
"""

CODEX_STABILIZE_PATH_UNIT = """[Unit]
Description=Watch Omarchy Codex usage record for intermittent account/read failures

[Path]
PathChanged={codex_record}
Unit=lemoria-codex-stabilize.service

[Install]
WantedBy=default.target
"""


def default_unit_dir() -> Path:
    return Path.home() / ".config" / "systemd" / "user"


def find_executable() -> str:
    """Absolute path to the lemoria CLI, for a unit that runs without a shell."""
    found = shutil.which("lemoria")
    if found:
        return found
    candidate = Path(sys.executable).parent / "lemoria"
    if candidate.exists():
        return str(candidate)
    return sys.executable


def install_codex_stabilizer(unit_dir: Path | None = None) -> tuple[Path, Path]:
    """Write user units that sanitize Codex immediately after native updates."""
    directory = unit_dir or default_unit_dir()
    directory.mkdir(parents=True, exist_ok=True)
    service = directory / "lemoria-codex-stabilize.service"
    path = directory / "lemoria-codex-stabilize.path"
    service.write_text(
        CODEX_STABILIZE_SERVICE_UNIT.format(executable=find_executable()),
        encoding="utf-8",
    )
    path.write_text(
        CODEX_STABILIZE_PATH_UNIT.format(codex_record=native_codex_record_path()),
        encoding="utf-8",
    )
    return service, path


def install_timer(unit_dir: Path | None = None, interval: str = "1min") -> tuple[Path, Path]:
    """Write the user-level units that keep the panel record fresh.

    Returns (service_path, timer_path). Enabling the timer is left to the
    caller so writing files never has the side effect of starting anything.
    """
    directory = unit_dir or default_unit_dir()
    directory.mkdir(parents=True, exist_ok=True)
    service = directory / "lemoria-usage.service"
    timer = directory / "lemoria-usage.timer"
    service.write_text(SERVICE_UNIT.format(executable=find_executable()), encoding="utf-8")
    timer.write_text(
        TIMER_UNIT.replace("OnUnitActiveSec=1min", f"OnUnitActiveSec={interval}"),
        encoding="utf-8",
    )
    return service, timer
