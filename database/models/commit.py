import uuid
from sqlalchemy import String, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin


class Commit(TimestampMixin, Base):
    __tablename__ = "commits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id"), nullable=True)
    sha: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=True)
    branch: Mapped[str] = mapped_column(String(255), nullable=True)
    repo_url: Mapped[str] = mapped_column(String(1024), nullable=True)
    committed_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)

    task = relationship("Task", back_populates="commits")
    files = relationship("FileRecord", back_populates="commit")
    push = relationship("Push", back_populates="commit", uselist=False)


class Push(TimestampMixin, Base):
    __tablename__ = "pushes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    commit_id: Mapped[str] = mapped_column(String(36), ForeignKey("commits.id"), nullable=False)
    remote: Mapped[str] = mapped_column(String(1024), nullable=True)
    branch: Mapped[str] = mapped_column(String(255), nullable=True)
    pr_url: Mapped[str] = mapped_column(String(1024), nullable=True)
    pushed_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)

    commit = relationship("Commit", back_populates="push")
