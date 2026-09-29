"""Publish Lemoria's opencode usage to the Omarchy agents panel.

Omarchy's agents panel is a display: it watches
``$XDG_STATE_HOME/omarchy/agents/usage/*.json`` and draws whatever records
appear there, regardless of who wrote them. The panel's own README documents
this as the supported way to add a provider, so Lemoria writes a record
instead of shipping a collector into ``/usr/share/omarchy/bin`` (read-only,
and lost on the next ``omarchy update``).

The contract below is what ``Main.qml``'s ``displayProvider()`` reads. Fields
it does not know are ignored, but every field it does read is emitted with the
exact name and type it expects, including the bucket keys under
``modelUsage``.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

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
    state_home = os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state")
    return Path(state_home) / "omarchy" / "agents" / "usage"


def build_record(telemetry: Telemetry) -> dict:
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
        # Lemoria drives no subscription, so there is no plan, no limit
        # window and no balance to report. Empty is the honest answer and the
        # panel renders the tab without a hero meter.
        "tierLabel": "",
        "usageStatusText": "" if telemetry.available else "opencode data unavailable",
        "authHelpText": telemetry.reason,
        "limits": [],
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
        # Not part of the panel's contract: the panel ignores unknown keys, but
        # they make the record self-describing for anything else that reads it.
        "totalTokens": telemetry.total_tokens,
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
    destination = output or (default_record_dir() / f"{AGENT_ID}.json")
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
    telemetry = OpenCodeTelemetry(db_path).read()
    record = build_record(telemetry)
    return write_record(record, Path(output) if output else None), record


SERVICE_UNIT = """[Unit]
Description=Publish lemoria opencode usage to the Omarchy panel

[Service]
Type=oneshot
ExecStart={executable} omarchy record
"""

TIMER_UNIT = """[Unit]
Description=Refresh the Omarchy agents panel

[Timer]
OnBootSec=1min
OnUnitActiveSec=1min
Persistent=true
Unit=lemoria-usage.service

[Install]
WantedBy=timers.target
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
