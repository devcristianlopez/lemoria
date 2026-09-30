"""Sync opencode agent definitions (markdown) to the database.

opencode reads agents from ``.opencode/agents/*.md``; Lemoria needs the same
facts in Postgres so it can export them to the vault, attribute work to them
and report on them. The markdown file stays the source of truth: this module
only mirrors it, and the one thing it writes back (``model``) edits
frontmatter in place rather than re-dumping YAML, so comments, key order and
folded scalars survive untouched.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DELIMITER = "---"
# A top-level key: no leading whitespace. Anchoring this matters, otherwise a
# nested `model:` under some other mapping would match and get rewritten.
_TOP_LEVEL_KEY = re.compile(r"^(?P<key>[A-Za-z_][\w-]*):(?P<rest>.*)$")
# The convention the existing agent files use to state their role in prose.
_ROLE_LINE = re.compile(r"^\*\*Role:\*\*\s*(?P<role>.+?)\s*$", re.MULTILINE)


@dataclass
class AgentDefinition:
    """One parsed agent markdown file."""

    name: str
    path: Path
    description: str | None = None
    role: str = ""
    mode: str | None = None
    model: str | None = None
    variant: str | None = None
    permission: dict = field(default_factory=dict)
    permissions: list[dict[str, str]] = field(default_factory=list)

    @property
    def config(self) -> dict:
        config = {
            "source": "sync",
            "mode": self.mode,
            "permissions": self.permissions,
        }
        if self.permission:
            config["permission"] = self.permission
        return config


_V1_TO_V2_ACTION = {
    "bash": "shell",
    "shell": "shell",
    "edit": "edit",
    "subtask": "subagent",
    "task": "subagent",
    "subagent": "subagent",
}
_V2_TO_V1_ACTION = {"shell": "bash", "edit": "edit", "subagent": "subagent"}


def _permission_rule(action: str, resource: str, effect: str) -> dict[str, str] | None:
    mapped_action = _V1_TO_V2_ACTION.get(action)
    if mapped_action is None or not effect:
        return None
    return {"action": mapped_action, "resource": resource or "*", "effect": effect}


def _permissions_from_legacy(permission: object) -> list[dict[str, str]]:
    if not isinstance(permission, dict):
        return []
    rules: list[dict[str, str]] = []
    for action, value in permission.items():
        if not isinstance(action, str):
            continue
        if isinstance(value, str):
            rule = _permission_rule(action, "*", value)
            if rule is not None:
                rules.append(rule)
            continue
        if isinstance(value, dict):
            for resource, effect in value.items():
                if isinstance(resource, str) and isinstance(effect, str):
                    rule = _permission_rule(action, resource, effect)
                    if rule is not None:
                        rules.append(rule)
    return rules


def _parse_permissions(permissions: object) -> list[dict[str, str]]:
    if not isinstance(permissions, list):
        return []
    rules: list[dict[str, str]] = []
    for item in permissions:
        if not isinstance(item, dict):
            continue
        action = item.get("action")
        effect = item.get("effect")
        resource = item.get("resource", "*")
        if isinstance(action, str) and isinstance(effect, str) and isinstance(resource, str):
            rules.append({"action": action, "resource": resource or "*", "effect": effect})
    return rules


def _legacy_permission_from_permissions(permissions: list[dict[str, str]]) -> dict:
    legacy: dict[str, str | dict[str, str]] = {}
    for rule in permissions:
        action = _V2_TO_V1_ACTION.get(rule["action"])
        if action is None:
            continue
        resource = rule["resource"]
        effect = rule["effect"]
        if resource == "*":
            legacy[action] = effect
            continue
        current = legacy.get(action)
        if not isinstance(current, dict):
            current = {}
            legacy[action] = current
        current[resource] = effect
    return legacy


def _split_frontmatter(raw: str) -> tuple[list[str], list[str]]:
    """Return (frontmatter_lines, everything_else) without reformatting either.

    Splitting on the delimiter as a whole string corrupts any body that itself
    contains `---` (a markdown rule), so split line by line instead.
    """
    lines = raw.splitlines(keepends=True)
    if not lines or lines[0].strip() != DELIMITER:
        return [], lines

    for index in range(1, len(lines)):
        if lines[index].strip() == DELIMITER:
            return lines[1:index], lines[index + 1 :]
    return [], lines


def _parse_role(body: str, fallback: str) -> str:
    """Prefer an explicit frontmatter role, then the `**Role:**` convention,
    then the filename stem. Never empty: `agents.role` is NOT NULL."""
    match = _ROLE_LINE.search(body)
    if match:
        return match.group("role")
    return fallback


def split_model_variant(model: object, variant: object = None) -> tuple[str | None, str | None]:
    """Return Lemoria's internal (model, variant) from OpenCode frontmatter.

    OpenCode v2 encodes reasoning effort as ``provider/model#variant``. Older
    files used a separate ``variant`` key, so keep reading that shape as a
    fallback while normalizing v2 strings for the database and UI.
    """
    parsed_model = model.strip() if isinstance(model, str) and model.strip() else None
    parsed_variant = variant.strip() if isinstance(variant, str) and variant.strip() else None
    if parsed_model is None:
        return None, parsed_variant
    if "#" not in parsed_model:
        return parsed_model, parsed_variant
    base_model, encoded_variant = parsed_model.rsplit("#", 1)
    return base_model or None, encoded_variant or parsed_variant


def join_model_variant(model: str | None, variant: str | None = None) -> str | None:
    """Encode Lemoria's internal model/variant split for OpenCode v2."""
    if model is None:
        return None
    if variant:
        return f"{model}#{variant}"
    return model


def parse_agent(path: Path) -> AgentDefinition | None:
    """Parse one agent markdown file. Returns None for an unreadable or
    frontmatter-less file rather than raising: a stray notes.md in the
    directory should not abort a whole sync."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None

    fm_lines, rest = _split_frontmatter(raw)
    if not fm_lines:
        return None

    try:
        data = yaml.safe_load("".join(fm_lines)) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None

    body = "".join(rest)
    name = path.stem
    # Folded scalars arrive already joined by safe_load, but be defensive: a
    # frontmatter that literally says `description: >-` yields ">-".
    description = data.get("description")
    if not isinstance(description, str) or description.strip() in {"", ">", ">-", "|", "|-"}:
        description = None

    legacy_permission = data.get("permission")
    permissions = _parse_permissions(data.get("permissions"))
    if not permissions:
        permissions = _permissions_from_legacy(legacy_permission)
    permission = (
        legacy_permission if isinstance(legacy_permission, dict)
        else _legacy_permission_from_permissions(permissions)
    )
    model, variant = split_model_variant(data.get("model"), data.get("variant"))
    return AgentDefinition(
        name=name,
        path=path,
        description=description,
        role=_parse_role(body, name),
        mode=data.get("mode"),
        model=model,
        variant=variant,
        permission=permission,
        permissions=permissions,
    )


def set_frontmatter_field(raw: str, key: str, value: str | None) -> str:
    """Set or remove one top-level frontmatter key, preserving everything else.

    Rewriting via yaml.dump would reflow `description: >-` into a quoted blob
    and drop comments, so this edits the existing lines in place and appends
    only when the key is absent.
    """
    fm_lines, rest = _split_frontmatter(raw)
    if not fm_lines:
        raise ValueError("file has no frontmatter block")

    kept: list[str] = []
    replaced = False
    for line in fm_lines:
        match = _TOP_LEVEL_KEY.match(line.rstrip("\n"))
        if match and match.group("key") == key:
            replaced = True
            if value is not None:
                kept.append(f"{key}: {value}\n")
            # value None means "remove the key": drop the line.
            continue
        kept.append(line)

    if value is not None and not replaced:
        # Append at the end of the block. Inserting "after the last top-level
        # key" looks tidier but lands *inside* whatever nested mapping follows
        # it -- `permission:` followed by indented `bash:`/`edit:` -- which is
        # a YAML syntax error. A column-0 key at the end always closes the
        # previous block cleanly.
        kept.append(f"{key}: {value}\n")

    return DELIMITER + "\n" + "".join(kept) + DELIMITER + "\n" + "".join(rest)


class AgentSync:
    """Mirrors .opencode/agents/*.md into the agents table."""

    def __init__(self, session, agents_dir: Path):
        self.session = session
        self.agents_dir = Path(agents_dir)

    def discover(self) -> list[AgentDefinition]:
        if not self.agents_dir.is_dir():
            return []
        found = []
        for path in sorted(self.agents_dir.glob("*.md")):
            definition = parse_agent(path)
            if definition is not None:
                found.append(definition)
        return found

    def sync(self, dry_run: bool = False) -> dict:
        """Upsert every discovered agent and deactivate the ones whose file
        disappeared. Idempotent: a second run over unchanged files is a no-op.

        Only agents this module wrote (``config.source == "sync"``) are ever
        deactivated, so an agent registered by hand survives even though no
        markdown file backs it.
        """
        from database.models.agent import Agent

        definitions = self.discover()
        report = {"created": [], "updated": [], "deactivated": [], "unchanged": []}

        existing = {a.name: a for a in self.session.query(Agent).all()}

        for definition in definitions:
            payload = {
                "role": definition.role,
                "description": definition.description,
                "active": True,
                "model": definition.model,
                "variant": definition.variant,
                "config": json.dumps(definition.config),
            }
            agent = existing.get(definition.name)

            if agent is None:
                if not dry_run:
                    agent = Agent(name=definition.name, **payload)
                    self.session.add(agent)
                report["created"].append(definition.name)
                continue

            changed = [
                field_name
                for field_name, value in payload.items()
                if getattr(agent, field_name) != value
            ]
            if not changed:
                report["unchanged"].append(definition.name)
                continue

            report["updated"].append(definition.name)
            if not dry_run:
                for field_name in changed:
                    setattr(agent, field_name, payload[field_name])

        synced_names = {d.name for d in definitions}
        for name, agent in existing.items():
            if name in synced_names or not agent.active:
                continue
            if agent.config_dict.get("source") != "sync":
                continue  # registered by hand, not ours to retire
            report["deactivated"].append(name)
            if not dry_run:
                agent.active = False

        if not dry_run:
            self.session.commit()
        return report

    def set_model(self, name: str, model: str | None, variant: str | None = None) -> AgentDefinition:
        """Point an agent at a model (or clear it) by editing its markdown.

        model=None with variant=None clears both, which restores inheritance
        from the invoking agent. This only touches the file: call sync()
        afterwards to mirror the change into the database.
        """
        path = self.agents_dir / f"{name}.md"
        if not path.is_file():
            raise FileNotFoundError(f"no agent file at {path}")

        raw = path.read_text(encoding="utf-8")
        raw = set_frontmatter_field(raw, "model", join_model_variant(model, variant))
        raw = set_frontmatter_field(raw, "variant", None)
        path.write_text(raw, encoding="utf-8")

        definition = parse_agent(path)
        if definition is None:
            raise ValueError(f"{path} has unparseable frontmatter after edit")
        return definition

    def set_effort(self, name: str, effort: str | None) -> AgentDefinition:
        """Set or clear an agent's reasoning effort while preserving its model."""
        path = self.agents_dir / f"{name}.md"
        definition = parse_agent(path) if path.is_file() else None
        if definition is None:
            raise FileNotFoundError(f"no parseable agent file at {path}")
        if definition.model is None and effort is not None:
            raise ValueError("cannot set effort without a pinned model")
        return self.set_model(name, definition.model, effort)
