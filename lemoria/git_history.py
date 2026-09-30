"""Read commit metadata out of a git repository.

Lemoria records a commit so it can be traced back to a task. The commit's
message, author, branch and timestamp already exist in git, and the sha is
the one thing a caller has to supply, so they are read from the repository
instead of asked for again: asking for them invites typos that silently
corrupt the traceability chain.

This module only talks to git. It knows nothing about the database; turning
what it reads into rows is ``GitService``'s job. Reading is done with
GitPython, not ``subprocess``, so output parsing (and its locale and
encoding assumptions) stays out of the codebase.
"""

from __future__ import annotations

import configparser
import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from git import Repo
from git.exc import BadName, GitError, InvalidGitRepositoryError, NoSuchPathError

# The trailer github-agent writes into commit messages so `commit sync` can
# recover the link between a commit and the task it implements. Anchored to
# the start of a line so prose like "see task: whatever" is not mistaken for
# one, and restricted to id-shaped tokens so the literal "<task-id>" from the
# agent's own documentation is not treated as a reference.
_TASK_TRAILER = re.compile(
    r"^task:[ \t]*(?P<ref>[A-Za-z0-9][A-Za-z0-9_-]*)[ \t]*(?:#.*)?$",
    re.MULTILINE | re.IGNORECASE,
)

# git refuses to give a commit an empty message only with an explicit flag, so
# the column (NOT NULL) still needs a placeholder.
NO_MESSAGE = "(sin mensaje)"


class GitHistoryError(Exception):
    """Base class for every failure reading git. The CLI renders these."""


class NotAGitRepository(GitHistoryError):
    def __init__(self, path: Path):
        self.path = Path(path)
        super().__init__(f"{self.path} is not inside a git repository")


class CommitNotFound(GitHistoryError):
    def __init__(self, sha: str, repo_dir: Path):
        self.sha = sha
        self.repo_dir = Path(repo_dir)
        super().__init__(f"commit '{sha}' does not exist in {self.repo_dir}")


class UnknownRevision(GitHistoryError):
    def __init__(self, revision: str, repo_dir: Path):
        self.revision = revision
        self.repo_dir = Path(repo_dir)
        super().__init__(f"revision '{revision}' does not exist in {self.repo_dir}")


@dataclass(frozen=True)
class CommitMeta:
    """One commit as git describes it, plus the task its message points at."""

    sha: str
    message: str
    author: str | None = None
    branch: str | None = None
    committed_at: datetime | None = None
    repo_url: str | None = None
    task_ref: str | None = None

    @property
    def subject(self) -> str:
        """The first line of the message.

        Bodies carry the `Task:` trailer and multi-line prose; dropping them
        keeps a commit readable on a single terminal line.
        """
        lines = self.message.strip().splitlines()
        return lines[0].strip() if lines else ""

    def with_overrides(
        self,
        message: str | None = None,
        author: str | None = None,
        branch: str | None = None,
        repo_url: str | None = None,
    ) -> CommitMeta:
        """Return a copy where each non-None argument replaces git's answer.

        Explicit flags are corrections, not defaults, so an absent flag must
        leave the value git gave untouched.
        """
        return replace(
            self,
            message=message or self.message,
            author=author or self.author,
            branch=branch or self.branch,
            repo_url=repo_url or self.repo_url,
        )


def _as_utc(moment: datetime | None) -> datetime | None:
    """Normalize git's tzinfo to a stdlib one psycopg accepts.

    GitPython returns a `git.objects.util.tzoffset`, a tzinfo subclass that
    the DB driver does not understand. A commit with no offset at all is read
    as UTC rather than left naive, since the column is timestamptz.
    """
    if moment is None:
        return None
    offset = moment.utcoffset()
    if offset is None:
        return moment.replace(tzinfo=UTC)
    if offset == timedelta(0):
        return moment.replace(tzinfo=UTC)
    return moment.replace(tzinfo=timezone(offset))


class CommitReader:
    """Reads commits from one repository."""

    def __init__(self, repo: Repo):
        self._repo = repo

    @classmethod
    def open(cls, path: Path | str | None = None) -> CommitReader:
        """Open the repository at `path` (or the current directory).

        Parent directories are searched so the command works from anywhere
        inside a repo, which is where an agent actually runs.
        """
        target = Path(path) if path is not None else Path.cwd()
        try:
            return cls(Repo(str(target), search_parent_directories=True))
        except (InvalidGitRepositoryError, NoSuchPathError) as error:
            raise NotAGitRepository(target) from error

    @property
    def workdir(self) -> Path:
        return Path(self._repo.working_dir or ".")

    @property
    def remote_url(self) -> str | None:
        """The remote to attribute commits to, preferring `origin`."""
        remotes = list(self._repo.remotes)
        if not remotes:
            return None
        remote = next((r for r in remotes if r.name == "origin"), remotes[0])
        try:
            url = remote.url
        except (GitError, configparser.Error):
            return None
        return url.strip() or None if isinstance(url, str) else None

    def read(self, sha: str) -> CommitMeta:
        """Read a single commit by sha (or any revision git accepts)."""
        try:
            commit = self._repo.commit(sha)
        except (BadName, GitError, ValueError) as error:
            raise CommitNotFound(sha, self.workdir) from error
        return self._meta(commit, branch=self.branch())

    def history(self, branch: str | None = None, limit: int | None = None) -> list[CommitMeta]:
        """Walk history newest first, defaulting to the checked-out branch."""
        revision = branch or self.branch()
        if limit is not None and limit < 1:
            raise ValueError("limit must be at least 1")
        try:
            commits = self._repo.iter_commits(revision, max_count=limit)
            return [self._meta(commit, branch=revision) for commit in commits]
        except (BadName, GitError, ValueError) as error:
            raise UnknownRevision(revision, self.workdir) from error

    def branch(self) -> str | None:
        """The branch commits should be attributed to.

        Falls back to HEAD when detached: the commits are still real, only
        the branch name is unknown.
        """
        try:
            return str(self._repo.active_branch)
        except (TypeError, GitError):
            return "HEAD"

    def _meta(self, commit, branch: str | None) -> CommitMeta:
        message = (commit.message or "").strip() or NO_MESSAGE
        author = None
        if commit.author:
            email = getattr(commit.author, "email", None)
            name = getattr(commit.author, "name", None) or str(commit.author)
            author = f"{name} <{email}>" if email else name
        return CommitMeta(
            sha=commit.hexsha,
            message=message,
            author=author,
            branch=branch,
            committed_at=_as_utc(commit.committed_datetime),
            repo_url=self.remote_url,
            task_ref=self.task_ref(message),
        )

    @staticmethod
    def task_ref(message: str) -> str | None:
        """The task id a commit message points at, if it points at one."""
        match = _TASK_TRAILER.search(message or "")
        return match.group("ref") if match else None
