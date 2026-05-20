from pathlib import Path
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
