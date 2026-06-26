"""Tests for VaultService."""

from pathlib import Path
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
