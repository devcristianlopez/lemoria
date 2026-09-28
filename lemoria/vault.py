import re
from pathlib import Path

_MARKER = "# Lemoria vault — added automatically by VaultService.protect_from_git()"


class VaultService:
    def __init__(self, vault_path: Path):
        self.vault_path = Path(vault_path)
        self._git_protected = False
        self._git_warnings: list[str] = []

    # ------------------------------------------------------------------
    # Git safety
    # ------------------------------------------------------------------
    def _find_git_root(self) -> Path | None:
        """Walk up from the vault looking for a git repo root."""
        current = self.vault_path.resolve() if self.vault_path.is_absolute() else Path.cwd() / self.vault_path
        for candidate in [current, *current.parents]:
            if (candidate / ".git").exists():
                return candidate
        return None

    def protect_from_git(self) -> str | None:
        """Make sure the vault can never be committed to git.

        If the vault path lives inside a git repo, add it to that repo's
        .gitignore. Runs once per process and never raises: a read-only
        repo produces a warning, not a crash.

        Returns a human-readable note when action was taken, else None.
        """
        if self._git_protected:
            return None
        self._git_protected = True

        git_root = self._find_git_root()
        if git_root is None:
            return None

        vault_abs = self.vault_path.resolve() if self.vault_path.is_absolute() else (Path.cwd() / self.vault_path).resolve()
        try:
            rel = vault_abs.relative_to(git_root)
        except ValueError:
            return None

        rel_str = rel.as_posix()
        if not rel_str or rel_str == ".":
            note = (
                f"Vault path is the git repo root itself ({git_root}). "
                "Refusing to ignore the whole repo — move LEMORIA_VAULT_PATH somewhere else."
            )
            self._git_warnings.append(note)
            return note

        gitignore = git_root / ".gitignore"
        entry = f"{rel_str}/"

        existing = ""
        if gitignore.exists():
            try:
                existing = gitignore.read_text(encoding="utf-8")
            except OSError as exc:
                note = f"Could not read {gitignore}: {exc}"
                self._git_warnings.append(note)
                return note

        ignored = {
            line.strip().rstrip("/")
            for line in existing.splitlines()
            if line.strip() and not line.strip().startswith("#")
        }
        if rel_str in ignored or entry in ignored:
            return None

        block = f"{existing.rstrip()}\n" if existing.strip() else ""
        block += f"\n{_MARKER}\n{entry}\n"

        try:
            gitignore.write_text(block, encoding="utf-8")
        except OSError as exc:
            note = f"Could not write {gitignore} ({exc}). Add '{entry}' manually to avoid committing your vault."
            self._git_warnings.append(note)
            return note

        return f"Vault is inside a git repo — added '{entry}' to {gitignore}"

    @property
    def warnings(self) -> list[str]:
        return list(self._git_warnings)

    # ------------------------------------------------------------------
    # Helpers de wikilinks para Obsidian
    # ------------------------------------------------------------------
    @staticmethod
    def sanitize_name(name: str) -> str:
        """Reduce a project name to a single safe path segment.

        Separators are flattened and traversal is dropped, so a project can
        never add nesting depth to its folder or escape the vault. This is
        what keeps "projects/lemoria" from becoming projects/projects/lemoria.
        """
        cleaned = str(name).strip()
        cleaned = cleaned.replace("\\", "-").replace("/", "-")
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", cleaned)
        cleaned = cleaned.strip(".-")
        while "--" in cleaned:
            cleaned = cleaned.replace("--", "-")
        return cleaned or "untitled"

    @staticmethod
    def wikilink(rel_path: str, text: str) -> str:
        """Genera un [[wikilink]] de Obsidian: [[ruta|texto]]."""
        return f"[[{rel_path}|{text}]]"

    @staticmethod
    def entity_path(project_name: str, entity_type: str, entity_id: str = "") -> str:
        """Resuelve la ruta relativa de una entidad dentro del vault."""
        base = f"projects/{VaultService.sanitize_name(project_name)}"
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
        self.protect_from_git()

    def write_note(self, relative_path: str, content: str) -> Path:
        full_path = self.vault_path / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        self.protect_from_git()
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
        project_name = self.sanitize_name(project_name)
        return self.write_note(f"projects/{project_name}/README.md", content)

    def export_conversation(self, project_name: str, conversation_id: str, content: str) -> Path:
        project_name = self.sanitize_name(project_name)
        return self.write_note(f"projects/{project_name}/conversations/{conversation_id}.md", content)

    def export_prd(self, project_name: str, prd_id: str, content: str) -> Path:
        project_name = self.sanitize_name(project_name)
        return self.write_note(f"projects/{project_name}/prds/{prd_id}.md", content)

    def export_decision(self, project_name: str, decision_id: str, title: str, description: str, rationale: str | None = None, status: str = "proposed") -> Path:
        project_name = self.sanitize_name(project_name)
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
        project_name = self.sanitize_name(project_name)
        project_link = self.project_wikilink(project_name)
        lines = ["# Agents\n", f"**Proyecto**: {project_link}\n\n"]
        for a in agents:
            desc = f" - {a['description']}" if a.get("description") else ""
            lines.append(f"- **{a['name']}** (`{a['role']}`){desc}")
        content = "\n".join(lines)
        return self.write_note(f"projects/{project_name}/agents.md", content)

    def export_tasks(self, project_name: str, tasks: list[dict]) -> Path:
        project_name = self.sanitize_name(project_name)
        project_link = self.project_wikilink(project_name)
        lines = ["# Tasks\n", f"**Proyecto**: {project_link}\n\n"]
        for t in tasks:
            desc = f": {t['description']}" if t.get("description") else ""
            lines.append(f"- **{t['title']}** [{t['status']}]{desc}")
        content = "\n".join(lines)
        return self.write_note(f"projects/{project_name}/tasks.md", content)

    def export_commits(self, project_name: str, commits: list[dict]) -> Path:
        project_name = self.sanitize_name(project_name)
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
        project_name = self.sanitize_name(project_name)
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
        project_name = self.sanitize_name(project_name)
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
