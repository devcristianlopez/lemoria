"""Tests for FlowEngine."""

from pathlib import Path

from database.enums import FlowStepStatus, PRDStatus, TaskStatus
from lemoria.git_history import CommitMeta
from lemoria.git_service import GitService
from lemoria.vault import VaultService


class TestFlowEngine:
    """Test the core flow engine operations."""

    def test_start_flow(self, flow_engine, project):
        """Should create a PRD with draft status."""
        prd = flow_engine.start_flow(project.id, "Test feature idea")
        assert prd.project_id == project.id
        assert prd.status == PRDStatus.DRAFT
        assert prd.id is not None

    def test_advance_prd(self, flow_engine, prd):
        """Should advance PRD from draft to active."""
        flow_engine.advance(prd.id)
        assert prd.status == PRDStatus.ACTIVE

    def test_complete_prd(self, flow_engine, prd):
        """Should complete a PRD."""
        flow_engine.complete(prd.id)
        assert prd.status == PRDStatus.COMPLETED

    def test_list_prds(self, flow_engine, project, prd):
        """Should list PRDs for a project."""
        prds = flow_engine.list_prds(project.id)
        assert len(prds) >= 1
        assert prds[0].id == prd.id

    def test_create_task(self, flow_engine, project, prd):
        """Should create a task linked to a PRD."""
        task = flow_engine.create_task(project.id, prd.id, None, "Test task")
        assert task.title == "Test task"
        assert task.status == TaskStatus.PENDING
        assert task.prd_id == prd.id

    def test_set_task_status(self, flow_engine, project, prd):
        """Should update task status."""
        task = flow_engine.create_task(project.id, prd.id, None, "Test task")
        result = flow_engine.set_task_status(task.id, TaskStatus.COMPLETED)
        assert result is not None
        assert result.status == TaskStatus.COMPLETED

    def test_set_task_status_not_found(self, flow_engine):
        """Should return None for non-existent task."""
        result = flow_engine.set_task_status("nonexistent", TaskStatus.COMPLETED)
        assert result is None


class TestFlowSteps:
    """Test the flow step state machine."""

    def test_start_step(self, flow_engine, prd):
        """Should create a step with running status."""
        step = flow_engine.start_step(prd.id, "implement")
        assert step.flow_id == prd.id
        assert step.step == "implement"
        assert step.status == FlowStepStatus.RUNNING
        assert step.started_at is not None

    def test_complete_step(self, flow_engine, prd):
        """Should create or update a step as completed."""
        step = flow_engine.complete_step(prd.id, "implement", "Done")
        assert step.status == FlowStepStatus.COMPLETED
        assert step.output == "Done"
        assert step.completed_at is not None

    def test_fail_step(self, flow_engine, prd):
        """Should create or update a step as failed."""
        step = flow_engine.fail_step(prd.id, "implement", "Error occurred")
        assert step.status == FlowStepStatus.FAILED
        assert step.output == "Error occurred"

    def test_get_flow_status_empty(self, flow_engine, prd):
        """Should return empty status for new flow."""
        status = flow_engine.get_flow_status(prd.id)
        assert status["flow_id"] == prd.id
        assert status["steps"] == []
        assert status["current_step"] is None
        assert status["completed"] is False

    def test_get_flow_status_with_steps(self, flow_engine, prd):
        """Should return correct status after steps."""
        flow_engine.complete_step(prd.id, "design", "Design done")
        flow_engine.start_step(prd.id, "implement")

        status = flow_engine.get_flow_status(prd.id)
        assert len(status["steps"]) == 2
        assert status["current_step"] == "implement"

    def test_get_or_create_step_reuses_existing(self, flow_engine, prd):
        """Should not duplicate steps with the same name."""
        s1 = flow_engine.complete_step(prd.id, "test", "Test 1")
        s2 = flow_engine.complete_step(prd.id, "test", "Test 2")
        assert s1.id == s2.id
        assert s2.output == "Test 2"


class TestDecisions:
    """Test decision recording."""

    def test_record_decision(self, flow_engine, project):
        """Should record a technical decision."""
        d = flow_engine.record_decision(
            project.id,
            "Use JWT for auth",
            "Stateless auth with refresh tokens",
            "Session-based auth is harder to scale"
        )
        assert d.project_id == project.id
        assert d.title == "Use JWT for auth"
        assert d.rationale == "Session-based auth is harder to scale"
        assert d.id is not None


class TestGitService:
    """Test commit traceability registration."""

    def test_record_commit_is_idempotent_by_sha(self, db_session, flow_engine, project, prd):
        task = flow_engine.create_task(project.id, prd.id, None, "Trace commits")
        service = GitService(db_session)
        meta = CommitMeta(
            sha="abc123",
            message="Implement traceability",
            author="Ada <ada@example.com>",
            branch="main",
        )

        first = service.record_commit(meta, task_id=task.id)
        second = service.record_commit(meta, task_id=task.id)

        assert first.created is True
        assert second.created is False
        assert db_session.query(first.commit.__class__).count() == 1
        assert first.commit.task_id == task.id

    def test_sync_history_reports_no_task_and_missing_task(self, db_session, flow_engine, project, prd):
        task = flow_engine.create_task(project.id, prd.id, None, "Linked task")
        service = GitService(db_session)
        history = [
            CommitMeta(sha="11111111", message=f"Linked\n\nTask: {task.id}", task_ref=task.id),
            CommitMeta(sha="22222222", message="No trailer"),
            CommitMeta(sha="33333333", message="Dangling\n\nTask: missing", task_ref="missing"),
        ]

        report = service.sync_history(history)

        assert report.scanned == 3
        assert len(report.inserted) == 3
        assert report.linked == ("11111111",)
        assert report.without_task == 1
        assert report.unknown_tasks == (("33333333", "missing"),)


class TestCommitVaultExport:
    """Test commit markdown export."""

    def test_export_commits_links_task_and_states_empty(self, tmp_path: Path):
        vault = VaultService(tmp_path)

        path = vault.export_commits(
            "Project X",
            [
                {
                    "sha": "abcdef123456",
                    "message": "Implement feature\n\nTask: task-id",
                    "author": "Ada",
                    "task_id": "task-id",
                    "task_title": "Build feature",
                }
            ],
        )
        content = path.read_text(encoding="utf-8")

        assert "`abcdef12` Implement feature" in content
        assert "[[projects/Project-X/tasks|Build feature]]" in content

        empty = vault.export_commits("Project X", [])
        assert "Sin commits registrados" in empty.read_text(encoding="utf-8")
