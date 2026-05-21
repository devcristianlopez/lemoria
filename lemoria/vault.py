from pathlib import Path


class VaultService:
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path

    def ensure_root(self) -> None:
        self.vault_path.mkdir(parents=True, exist_ok=True)

    def write_note(self, relative_path: str, content: str) -> Path:
        full_path = self.vault_path / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        return full_path

    def read_note(self, relative_path: str) -> str | None:
        full_path = self.vault_path / relative_path
        if full_path.exists():
            return full_path.read_text(encoding="utf-8")
        return None

    def list_notes(self, subdir: str = "") -> list[Path]:
        target = self.vault_path / subdir
        if not target.exists():
            return []
        return sorted(target.rglob("*.md"))

    def export_project_overview(self, project_name: str, content: str) -> Path:
        return self.write_note(f"projects/{project_name}/README.md", content)

    def export_conversation(self, project_name: str, conversation_id: str, content: str) -> Path:
        return self.write_note(f"projects/{project_name}/conversations/{conversation_id}.md", content)

    def export_prd(self, project_name: str, prd_id: str, content: str) -> Path:
        return self.write_note(f"projects/{project_name}/prds/{prd_id}.md", content)

    def export_decision(self, project_name: str, decision_id: str, title: str, description: str, rationale: str | None = None, status: str = "proposed") -> Path:
        content = f"""# ADR: {title}

**Status**: {status}
**ID**: {decision_id}

## Description

{description}

## Rationale

{rationale or "Not specified."}
"""
        return self.write_note(f"projects/{project_name}/decisions/{decision_id}.md", content)

    def export_agents(self, project_name: str, agents: list[dict]) -> Path:
        lines = ["# Agents\n"]
        for a in agents:
            desc = f" - {a['description']}" if a.get("description") else ""
            lines.append(f"- **{a['name']}** (`{a['role']}`){desc}")
        content = "\n".join(lines)
        return self.write_note(f"projects/{project_name}/agents.md", content)

    def export_tasks(self, project_name: str, tasks: list[dict]) -> Path:
        lines = ["# Tasks\n"]
        for t in tasks:
            desc = f": {t['description']}" if t.get("description") else ""
            lines.append(f"- **{t['title']}** [{t['status']}]{desc}")
        content = "\n".join(lines)
        return self.write_note(f"projects/{project_name}/tasks.md", content)

    def export_commits(self, project_name: str, commits: list[dict]) -> Path:
        lines = ["# Commits\n"]
        for c in commits:
            lines.append(f"- `{c['sha'][:8]}` {c['message']} ({c.get('author', '?')})")
        content = "\n".join(lines)
        return self.write_note(f"projects/{project_name}/commits.md", content)
