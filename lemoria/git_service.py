from sqlalchemy.orm import Session
from database.models.commit import Commit, Push
from database.models.file_record import FileRecord
from database.models.task import Task


class GitService:
    def __init__(self, session: Session):
        self.session = session

    def register_commit(
        self,
        sha: str,
        message: str,
        author: str | None = None,
        branch: str | None = None,
        repo_url: str | None = None,
        task_id: str | None = None,
    ) -> Commit:
        commit = Commit(
            sha=sha, message=message, author=author,
            branch=branch, repo_url=repo_url, task_id=task_id,
        )
        self.session.add(commit)
        self.session.commit()
        return commit

    def register_push(
        self,
        commit_id: str,
        remote: str | None = None,
        branch: str | None = None,
        pr_url: str | None = None,
    ) -> Push:
        push = Push(commit_id=commit_id, remote=remote, branch=branch, pr_url=pr_url)
        self.session.add(push)
        self.session.commit()
        return push

    def register_file_change(
        self,
        commit_id: str,
        path: str,
        status: str = "modified",
        additions: int = 0,
        deletions: int = 0,
    ) -> FileRecord:
        record = FileRecord(commit_id=commit_id, path=path, status=status, additions=additions, deletions=deletions)
        self.session.add(record)
        self.session.commit()
        return record

    def list_commits(self, task_id: str) -> list[Commit]:
        return self.session.query(Commit).filter(Commit.task_id == task_id).all()

    def get_commits_by_branch(self, branch: str) -> list[Commit]:
        return self.session.query(Commit).filter(Commit.branch == branch).all()
