"""Tests for VaultService."""

import os

import pytest

from database.enums import FlowStepStatus
from lemoria.vault import VaultService


class TestVaultService:
    """Test vault export operations."""

    def test_write_and_read_note(self, tmp_path):
        """Should write and read markdown notes."""
        vault = VaultService(tmp_path)
        path = vault.write_note("test/note.md", "# Hello")
        assert path.exists()
        content = vault.read_note("test/note.md")
        assert content == "# Hello"

    def test_read_nonexistent(self, tmp_path):
        """Should return None for missing notes."""
        vault = VaultService(tmp_path)
        assert vault.read_note("nonexistent.md") is None

    def test_list_notes_empty(self, tmp_path):
        """Should return empty list for empty vault."""
        vault = VaultService(tmp_path)
        assert vault.list_notes("empty") == []

    def test_list_notes(self, tmp_path):
        """Should list all markdown files."""
        vault = VaultService(tmp_path)
        vault.write_note("a/1.md", "# 1")
        vault.write_note("a/2.md", "# 2")
        notes = vault.list_notes("a")
        assert len(notes) == 2
        assert all(n.suffix == ".md" for n in notes)

    def test_wikilink(self):
        """Should generate [[wikilink|text]] format."""
        link = VaultService.wikilink("path/to/file", "Display Text")
        assert link == "[[path/to/file|Display Text]]"

    def test_entity_path(self):
        """Should resolve entity paths correctly."""
        assert VaultService.entity_path("myproj", "project") == "projects/myproj/README"
        assert VaultService.entity_path("myproj", "prd", "abc123") == "projects/myproj/prds/abc123"
        assert VaultService.entity_path("myproj", "decision", "def456") == "projects/myproj/decisions/def456"

    def test_project_wikilink(self):
        """Should generate project wikilink."""
        link = VaultService.project_wikilink("myproj")
        assert "myproj" in link
        assert "README" in link

    def test_parse_frontmatter_simple(self, tmp_path):
        """Should parse YAML frontmatter."""
        vault = VaultService(tmp_path)
        content = """---
id: abc-123
type: decision
status: accepted
---

# Title
Body text"""
        metadata, body = vault.parse_frontmatter(content)
        assert metadata["id"] == "abc-123"
        assert metadata["type"] == "decision"
        assert metadata["status"] == "accepted"
        assert "# Title" in body

    def test_parse_frontmatter_no_frontmatter(self, tmp_path):
        """Should return empty metadata if no frontmatter."""
        vault = VaultService(tmp_path)
        metadata, body = vault.parse_frontmatter("# Just a title")
        assert metadata == {}
        assert body == "# Just a title"

    def test_export_and_import_roundtrip(self, tmp_path):
        """Should export and allow reading back flow steps."""
        vault = VaultService(tmp_path)

        from database.models.flow_step import FlowStep
        # Create a mock step (not persisted, just for export)
        step = FlowStep(
            id="test-id-123",
            flow_id="flow-id-456",
            step="implement",
            status=FlowStepStatus.COMPLETED,
            output="Done with test"
        )

        vault.export_flow_steps("myproj", "Test PRD", [step])
        notes = vault.list_notes("projects/myproj/flow_steps")
        assert len(notes) == 1

        content = vault.read_note(str(notes[0].relative_to(vault.vault_path)))
        assert content is not None
        metadata, body = vault.parse_frontmatter(content)
        assert metadata["id"] == "test-id-123"
        assert "implement" in body

    def test_sanitize_name_prevents_path_traversal(self):
        """sanitize_name flattens nested paths to a single segment."""
        assert VaultService.sanitize_name("myproj") == "myproj"
        assert VaultService.sanitize_name("projects/lemoria") == "projects-lemoria"
        assert VaultService.sanitize_name("../etc/passwd") == "etc-passwd"
        assert VaultService.sanitize_name("../../vault") == "vault"
        assert VaultService.sanitize_name("lemoria///repo") == "lemoria-repo"
        assert VaultService.sanitize_name(".hidden/name") == "hidden-name"
        assert VaultService.sanitize_name("My Proj (v1)") == "My-Proj-v1"
        assert VaultService.sanitize_name("") == "untitled"

    def test_entity_path_sanitizes_project_name(self):
        """entity_path must not double-nest projects when name contains 'projects/'."""
        path = VaultService.entity_path("projects/lemoria", "project")
        assert path == "projects/projects-lemoria/README"
        path2 = VaultService.entity_path("../secret", "prd", "abc")
        assert path2 == "projects/secret/prds/abc"

    def test_exports_do_not_nest_written_paths(self, tmp_path):
        """Exporters write under the sanitized name, so nothing escapes projects/."""
        vault = VaultService(tmp_path)
        vault.export_project_overview("projects/lemoria", "# hi")
        vault.export_tasks("projects/lemoria", [{"title": "t", "status": "pending"}])
        vault.export_agents("projects/lemoria", [{"name": "a", "role": "r"}])

        written = sorted(p.relative_to(tmp_path).as_posix() for p in vault.list_notes(""))
        assert written == [
            "projects/projects-lemoria/README.md",
            "projects/projects-lemoria/agents.md",
            "projects/projects-lemoria/tasks.md",
        ]
        assert not (tmp_path / "projects" / "projects").exists()

    def test_exports_survive_hostile_project_name(self, tmp_path):
        """A traversal attempt is flattened into a single safe segment."""
        vault = VaultService(tmp_path)
        vault.export_project_overview("../../etc", "# pwn")
        assert (tmp_path / "projects" / "etc" / "README.md").exists()
        assert not (tmp_path.parent / "etc").exists()

    def test_protect_from_git_adds_gitignore_inside_repo(self, tmp_path):
        """If vault lives inside a git repo, .gitignore is updated automatically."""
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        vault_dir = repo / "private" / "vault"
        vault = VaultService(vault_dir)

        note = vault.protect_from_git()
        assert note is not None
        assert "private/vault/" in note
        gitignore = repo / ".gitignore"
        assert gitignore.exists()
        assert "private/vault/" in gitignore.read_text()

        # Idempotent: second call returns None and doesn't duplicate
        second = vault.protect_from_git()
        assert second is None
        text = gitignore.read_text()
        assert text.count("private/vault/") == 1

    def test_protect_from_git_does_not_modify_outside_repo(self, tmp_path):
        """Vault outside any repo remains untouched."""
        vault_dir = tmp_path / "vault-outside"
        vault = VaultService(vault_dir)
        result = vault.protect_from_git()
        assert result is None
        assert not (tmp_path / ".gitignore").exists()

    def test_protect_from_git_handles_unreadable_gitignore(self, tmp_path):
        """A broken .gitignore is surfaced as a warning, never raised.

        A directory named .gitignore makes read_text raise, standing in for
        any repo whose ignore file cannot be inspected.
        """
        repo = tmp_path / "repo-bad"
        repo.mkdir()
        (repo / ".git").mkdir()
        (repo / ".gitignore").mkdir()
        vault = VaultService(repo / "vault")

        res = vault.protect_from_git()
        assert res is not None
        assert "Could not read" in res
        assert res in vault.warnings

    @pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses file permissions")
    def test_protect_from_git_handles_unwritable_gitignore(self, tmp_path):
        """A read-only .gitignore yields a warning, never an exception."""
        repo = tmp_path / "repo-ro"
        repo.mkdir()
        (repo / ".git").mkdir()
        gitignore = repo / ".gitignore"
        gitignore.write_text("", encoding="utf-8")
        gitignore.chmod(0o444)
        try:
            vault = VaultService(repo / "vault")
            res = vault.protect_from_git()
            assert res is not None
            assert "Could not write" in res
            assert res in vault.warnings
        finally:
            gitignore.chmod(0o644)

    def test_protect_from_git_respects_existing_entry(self, tmp_path):
        """An entry already covering the vault is left alone."""
        repo = tmp_path / "repo-done"
        repo.mkdir()
        (repo / ".git").mkdir()
        (repo / ".gitignore").write_text("vault/\n", encoding="utf-8")
        vault = VaultService(repo / "vault")

        assert vault.protect_from_git() is None
        assert (repo / ".gitignore").read_text() == "vault/\n"

    def test_protect_from_git_warns_when_vault_is_repo_root(self, tmp_path):
        """Vault == git root cannot be ignored safely."""
        repo = tmp_path / "repo-root"
        repo.mkdir()
        (repo / ".git").mkdir()
        vault = VaultService(repo)
        res = vault.protect_from_git()
        assert res is not None
        assert "git repo root" in res
        assert res in vault.warnings
        assert not (repo / ".gitignore").exists()
