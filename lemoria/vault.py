from pathlib import Path


class VaultService:
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path

    # ------------------------------------------------------------------
    # Helpers de wikilinks para Obsidian
    # ------------------------------------------------------------------
    @staticmethod
    def wikilink(rel_path: str, text: str) -> str:
        """Genera un [[wikilink]] de Obsidian: [[ruta|texto]]."""
        return f"[[{rel_path}|{text}]]"

    @staticmethod
    def entity_path(project_name: str, entity_type: str, entity_id: str = "") -> str:
        """Resuelve la ruta relativa de una entidad dentro del vault."""
        base = f"projects/{project_name}"
        mapping = {
            "project": f"{base}/README",
            "prd": f"{base}/prds/{entity_id}",
            "decision": f"{base}/decisions/{entity_id}",
            "conversation": f"{base}/conversations/{entity_id}",
            "tasks": f"{base}/tasks",
            "commits": f"{base}/commits",
            "agents": f"{base}/agents",
            "flow_steps": f"{base}/flow_steps",
        }
        return mapping.get(entity_type, base)

    @staticmethod
    def project_wikilink(project_name: str) -> str:
        return VaultService.wikilink(
            VaultService.entity_path(project_name, "project"), project_name
        )

    @staticmethod
    def entity_wikilink(project_name: str, entity_type: str, entity_id: str, text: str) -> str:
        return VaultService.wikilink(
            VaultService.entity_path(project_name, entity_type, entity_id), text
        )

    # ------------------------------------------------------------------
    # Métodos de archivo
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Exportadores
    # ------------------------------------------------------------------
    def export_project_overview(self, project_name: str, content: str) -> Path:
        return self.write_note(f"projects/{project_name}/README.md", content)

    def export_conversation(self, project_name: str, conversation_id: str, content: str) -> Path:
        return self.write_note(f"projects/{project_name}/conversations/{conversation_id}.md", content)

    def export_prd(self, project_name: str, prd_id: str, content: str) -> Path:
        return self.write_note(f"projects/{project_name}/prds/{prd_id}.md", content)

    def export_decision(self, project_name: str, decision_id: str, title: str, description: str, rationale: str | None = None, status: str = "proposed") -> Path:
        project_link = self.project_wikilink(project_name)
        content = f"""---
id: {decision_id}
type: decision
status: {status}
project: {project_name}
---

# ADR: {title}

**Status**: {status}
**ID**: {decision_id}
**Proyecto**: {project_link}

## Description

{description}

## Rationale

{rationale or "Not specified."}
"""
        return self.write_note(f"projects/{project_name}/decisions/{decision_id}.md", content)

    def export_agents(self, project_name: str, agents: list[dict]) -> Path:
        project_link = self.project_wikilink(project_name)
        lines = ["# Agents\n", f"**Proyecto**: {project_link}\n\n"]
        for a in agents:
            desc = f" - {a['description']}" if a.get("description") else ""
            lines.append(f"- **{a['name']}** (`{a['role']}`){desc}")
        content = "\n".join(lines)
        return self.write_note(f"projects/{project_name}/agents.md", content)

    def export_tasks(self, project_name: str, tasks: list[dict]) -> Path:
        project_link = self.project_wikilink(project_name)
        lines = ["# Tasks\n", f"**Proyecto**: {project_link}\n\n"]
        for t in tasks:
            desc = f": {t['description']}" if t.get("description") else ""
            lines.append(f"- **{t['title']}** [{t['status']}]{desc}")
        content = "\n".join(lines)
        return self.write_note(f"projects/{project_name}/tasks.md", content)

    def export_commits(self, project_name: str, commits: list[dict]) -> Path:
        project_link = self.project_wikilink(project_name)
        tasks_link = self.wikilink(self.entity_path(project_name, "tasks"), "Tasks")
        lines = ["# Commits\n", f"**Proyecto**: {project_link}\n\n"]
        for c in commits:
            lines.append(f"- `{c['sha'][:8]}` {c['message']} ({c.get('author', '?')})")
        lines.append(f"\n---\nVolver a {tasks_link}")
        content = "\n".join(lines)
        return self.write_note(f"projects/{project_name}/commits.md", content)

    def export_flow_steps(self, project_name: str, prd_title: str, steps: list) -> Path:
        """Export flow steps for a PRD with frontmatter for restore."""
        # Build frontmatter for each step
        notes = []
        for s in steps:
            fm = f"""---
id: {s.id}
type: flow_step
flow_id: {s.flow_id}
step: {s.step}
status: {s.status}
---

# Step: {s.step}

**Flow**: {s.flow_id}
**Status**: {s.status}
**Started**: {s.started_at or 'N/A'}
**Completed**: {s.completed_at or 'N/A'}

## Output

{s.output or 'No output'}
"""
            notes.append(fm)

        # Write individual files per step
        for s, note in zip(steps, notes):
            self.write_note(f"projects/{project_name}/flow_steps/{s.id[:8]}_{s.step}.md", note)
        return self.vault_path / f"projects/{project_name}/flow_steps"

    # ------------------------------------------------------------------
    # Restore (vault → DB)
    # ------------------------------------------------------------------
    def restore_project(self, project_id: str, project_name: str) -> dict:
        """
        Restore project data from vault markdown files.
        Returns a dict with counts of restored entities.
        Note: this method only reads the vault and returns structured data.
        The caller (CLI) handles DB insertion.
        """
        restored = {"conversations": 0, "decisions": 0, "flow_steps": 0}

        # --- Decisions ---
        decision_dir = f"projects/{project_name}/decisions"
        for note_path in self.list_notes(decision_dir):
            content = self.read_note(str(note_path.relative_to(self.vault_path)))
            if content:
                restored["decisions"] += 1

        # --- Flow steps ---
        flow_dir = f"projects/{project_name}/flow_steps"
        for note_path in self.list_notes(flow_dir):
            restored["flow_steps"] += 1

        return restored

    def parse_frontmatter(self, content: str) -> tuple[dict, str]:
        """Parse Obsidian frontmatter from markdown content. Returns (metadata, body)."""
        if not content.startswith("---"):
            return {}, content
        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}, content
        metadata = {}
        for line in parts[1].strip().split("\n"):
            if ":" in line:
                key, _, value = line.partition(":")
                metadata[key.strip()] = value.strip().strip('"').strip("'")
        return metadata, parts[2].strip()
