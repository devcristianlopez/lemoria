"""Traceability: commits, and the task each one belongs to.

A commit row is worthless on its own -- the reason the ``commits`` table
exists is to answer "which task produced this sha" -- so linking is a first
class part of recording one, not an afterthought. Two entry points:

``record_commit``
    One commit, read from git, optionally linked to a task.
``sync_history``
    A whole branch, read from git, with the task recovered from the
    ``Task: <id>`` trailer github-agent already writes.

Both are idempotent by sha. Rerunning a sync over a repo whose commits are
mostly already recorded must not duplicate rows, and must not fail when a
commit message names a task the database has never heard of: that dangling
reference is reported, not silently dropped and not fatal.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import literal, or_
from sqlalchemy.orm import Session

from database.models.commit import Commit, Push
from database.models.file_record import FileRecord
from database.models.task import Task

from .git_history import CommitMeta


class RefError(LookupError):
    """A reference given to Lemoria points at nothing usable.

    The message is written for a terminal, not a traceback: every caller of
    these services is a click command.
    """


class UnknownTaskRef(RefError):
    def __init__(self, ref: str):
        self.ref = ref
        super().__init__(f"no task matches '{ref}'")


class AmbiguousRef(RefError):
    def __init__(self, ref: str, matches: list[str]):
        self.ref = ref
        self.matches = list(matches)
        super().__init__(f"'{ref}' matches {len(self.matches)} tasks: {', '.join(self.matches)}")


class AmbiguousSha(RefError):
    def __init__(self, sha: str, matches: list[str]):
        self.sha = sha
        self.matches = list(matches)
        super().__init__(f"sha '{sha}' matches {len(self.matches)} commits: {', '.join(self.matches)}")


@dataclass(frozen=True)
class RecordResult:
    """Outcome of recording one commit."""

    commit: Commit
    created: bool
    task_linked: bool = False
    task_conflict: str | None = None
    refreshed: tuple[str, ...] = ()


@dataclass(frozen=True)
class SyncReport:
    """What a sync did, or would have done under ``dry_run``."""

    scanned: int
    inserted: tuple[str, ...] = ()
    linked: tuple[str, ...] = ()
    refreshed: tuple[str, ...] = ()
    unchanged: int = 0
    without_task: int = 0
    unknown_tasks: tuple[tuple[str, str], ...] = ()
    dry_run: bool = False

    @property
    def skipped(self) -> int:
        """Commits already in the table, so nothing was added for them."""
        return self.scanned - len(self.inserted)


@dataclass(frozen=True)
class CommitRow:
    """A commit plus the title of the task it is linked to, if any."""

    commit: Commit
    task_title: str | None = None


class GitService:
    def __init__(self, session: Session):
        self.session = session

    # ── Reading ─────────────────────────────────────────────────────
    def get_commit_by_sha(self, sha: str) -> Commit | None:
        """The recorded commit for `sha`, full or abbreviated.

        Both directions of abbreviation are handled: the table may hold a full
        sha while the caller passed a short one, and rows written before full
        shas were stored hold the short one instead.
        """
        needle = (sha or "").strip().lower()
        if not needle:
            return None
        matches = (
            self.session.query(Commit)
            .filter(or_(Commit.sha.startswith(needle), literal(needle).like(Commit.sha)))
            .limit(4)
            .all()
        )
        exact = [c for c in matches if c.sha.lower() == needle]
        if len(exact) == 1:
            return exact[0]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise AmbiguousSha(needle, [c.sha for c in matches])
        return None

    def list_commits(
        self,
        project_id: str | None = None,
        task_id: str | None = None,
        limit: int | None = None,
    ) -> list[CommitRow]:
        """Commits newest first, optionally narrowed to a project or a task.

        A project filter follows the link commit -> task -> project, so it
        returns only the commits actually traced to that project; commits
        with no task belong to no project and drop out.
        """
        query = self.session.query(Commit, Task.title).outerjoin(Task, Commit.task_id == Task.id)
        if task_id:
            query = query.filter(Commit.task_id == task_id)
        if project_id:
            query = query.filter(Task.project_id == project_id)
        query = query.order_by(Commit.created_at.desc(), Commit.id)
        if limit is not None:
            query = query.limit(limit)
        return [CommitRow(commit=commit, task_title=title) for commit, title in query.all()]

    def list_commits_by_task(self, task_id: str) -> list[Commit]:
        return self.session.query(Commit).filter(Commit.task_id == task_id).all()

    def get_commits_by_branch(self, branch: str) -> list[Commit]:
        return self.session.query(Commit).filter(Commit.branch == branch).all()

    def resolve_task_id(self, ref: str) -> str:
        """Turn a task id, or an unambiguous prefix of one, into a task id.

        A short sha pasted from the terminal is the normal case, so prefixes
        resolve. Zero or many matches are errors: guessing would attach a
        commit to the wrong task, which is worse than not attaching it.
        """
        needle = (ref or "").strip()
        if not needle:
            raise UnknownTaskRef(ref)
        task = self.session.get(Task, needle)
        if task is not None:
            return task.id
        matches = self.session.query(Task).filter(Task.id.startswith(needle)).limit(2).all()
        if len(matches) == 1:
            return matches[0].id
        if len(matches) > 1:
            raise AmbiguousRef(needle, [t.id for t in matches])
        raise UnknownTaskRef(needle)

    # ── Writing ─────────────────────────────────────────────────────
    def record_commit(
        self,
        meta: CommitMeta,
        task_id: str | None = None,
        dry_run: bool = False,
    ) -> RecordResult:
        """Record one commit read from git, linking it to `task_id`.

        Idempotent by sha. A commit already in the table is never duplicated:
        its metadata is refreshed from git (git is the source of truth for
        message, author, branch and timestamp) and a task link that was
        missing is filled in. An existing link is never silently repointed --
        `task_conflict` reports the request so the caller can say so.
        """
        existing = self.get_commit_by_sha(meta.sha)
        if existing is None:
            commit = Commit(
                sha=meta.sha,
                message=meta.message,
                author=meta.author,
                branch=meta.branch,
                repo_url=meta.repo_url,
                committed_at=meta.committed_at,
                task_id=task_id,
            )
            if not dry_run:
                self.session.add(commit)
                self.session.commit()
            return RecordResult(commit=commit, created=True, task_linked=bool(task_id))

        refreshed = self._refresh(existing, meta, dry_run=dry_run)
        task_linked, task_conflict = self._link(existing, task_id, dry_run=dry_run)
        return RecordResult(
            commit=existing,
            created=False,
            task_linked=task_linked,
            task_conflict=task_conflict,
            refreshed=refreshed,
        )

    def sync_history(
        self,
        history: list[CommitMeta],
        dry_run: bool = False,
    ) -> SyncReport:
        """Record every commit in `history` that the table does not have yet.

        The task comes from the `Task: <id>` trailer in the commit message.
        When that trailer names a task the database does not have, the commit
        is still recorded and the dangling reference is reported: the history
        is real, and losing it would be worse than an incomplete link.
        """
        inserted: list[str] = []
        linked: list[str] = []
        refreshed: list[str] = []
        unknown: list[tuple[str, str]] = []
        without_task = 0
        unchanged = 0

        for meta in history:
            task_id = self._task_id_from_ref(meta)
            if meta.task_ref and task_id is None:
                unknown.append((meta.sha[:8], meta.task_ref))
            elif task_id is None:
                without_task += 1
            if task_id:
                linked.append(meta.sha[:8])

            result = self.record_commit(meta, task_id=task_id, dry_run=dry_run)
            if result.created:
                inserted.append(meta.sha[:8])
            elif result.refreshed:
                refreshed.append(meta.sha[:8])
            else:
                unchanged += 1

        return SyncReport(
            scanned=len(history),
            inserted=tuple(inserted),
            linked=tuple(linked),
            refreshed=tuple(refreshed),
            unchanged=unchanged,
            without_task=without_task,
            unknown_tasks=tuple(unknown),
            dry_run=dry_run,
        )

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

    # ── Internals ───────────────────────────────────────────────────
    def _task_id_from_ref(self, meta: CommitMeta) -> str | None:
        """Resolve the commit message's `Task:` trailer, if it resolves."""
        if not meta.task_ref:
            return None
        try:
            return self.resolve_task_id(meta.task_ref)
        except RefError:
            return None

    def _refresh(self, commit: Commit, meta: CommitMeta, dry_run: bool) -> tuple[str, ...]:
        """Copy git's answers onto an existing row. Returns what changed."""
        updated: list[str] = []
        for field_name, value in (
            ("message", meta.message),
            ("author", meta.author),
            ("branch", meta.branch),
            ("repo_url", meta.repo_url),
            ("committed_at", meta.committed_at),
        ):
            if value is None:
                continue
            if getattr(commit, field_name) == value:
                continue
            updated.append(field_name)
            if not dry_run:
                setattr(commit, field_name, value)
        if updated and not dry_run:
            self.session.commit()
        return tuple(updated)

    def _link(
        self,
        commit: Commit,
        task_id: str | None,
        dry_run: bool,
    ) -> tuple[bool, str | None]:
        """Attach a task to an existing commit. Returns (linked, conflict)."""
        if not task_id or commit.task_id == task_id:
            return False, None
        if commit.task_id:
            return False, task_id
        if not dry_run:
            commit.task_id = task_id
            self.session.commit()
        return True, None
