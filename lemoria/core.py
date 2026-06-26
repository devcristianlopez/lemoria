from .config import settings
from .database import init_db, get_session
from .project import ProjectService
from .memory import MemoryService
from .orchestrator import Orchestrator
from .flow import FlowEngine
from .vault import VaultService
from .git_service import GitService


class Lemoria:
    def __init__(self):
        self.session = get_session()
        self.projects = ProjectService(self.session)
        self.memory = MemoryService(self.session)
        self.orchestrator = Orchestrator(self.session)
        self.flow = FlowEngine(self.session)
        self.vault = VaultService(settings.vault_path)
        self.git = GitService(self.session)

    def init_system(self):
        init_db()
        self.vault.ensure_root()

    def close(self):
        self.session.close()

    def restore_from_vault(self, project_id: str, project_name: str) -> dict:
        """Restore project data from vault markdown files back to the database."""
        from database.models.decision import Decision
        from database.models.flow_step import FlowStep
        from database.enums import FlowStepStatus

        restored = {"decisions": 0, "flow_steps": 0}

        # --- Restore decisions from vault ---
        decision_dir = f"projects/{project_name}/decisions"
        for note_path in self.vault.list_notes(decision_dir):
            rel_path = str(note_path.relative_to(self.vault.vault_path))
            content = self.vault.read_note(rel_path)
            if not content:
                continue
            metadata, body = self.vault.parse_frontmatter(content)
            dec_id = metadata.get("id")
            status = metadata.get("status", "proposed")
            if not dec_id:
                continue
            # Extract title from the ADR heading
            title = "Restored decision"
            for line in body.split("\n"):
                if line.startswith("# ADR:"):
                    title = line.replace("# ADR:", "").strip()
                    break
            # Check if already exists
            existing = self.session.get(Decision, dec_id)
            if not existing:
                d = Decision(
                    id=dec_id,
                    project_id=project_id,
                    title=title,
                    description=body[:500],
                    status=status,
                )
                self.session.add(d)
                restored["decisions"] += 1

        # --- Restore flow steps from vault ---
        flow_dir = f"projects/{project_name}/flow_steps"
        for note_path in self.vault.list_notes(flow_dir):
            rel_path = str(note_path.relative_to(self.vault.vault_path))
            content = self.vault.read_note(rel_path)
            if not content:
                continue
            metadata, body = self.vault.parse_frontmatter(content)
            fs_id = metadata.get("id")
            if not fs_id:
                continue
            existing = self.session.get(FlowStep, fs_id)
            if not existing:
                fs = FlowStep(
                    id=fs_id,
                    flow_id=metadata.get("flow_id", project_id),
                    step=metadata.get("step", "unknown"),
                    status=metadata.get("status", FlowStepStatus.PENDING),
                )
                self.session.add(fs)
                restored["flow_steps"] += 1

        self.session.commit()
        return restored
