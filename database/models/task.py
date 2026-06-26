import uuid
from sqlalchemy import String, Text, ForeignKey, Integer, Boolean, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin
from database.enums import TaskStatus


class Task(TimestampMixin, Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    prd_id: Mapped[str] = mapped_column(String(36), ForeignKey("prds.id"), nullable=True)
    spec_id: Mapped[str] = mapped_column(String(36), ForeignKey("specs.id"), nullable=True)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=TaskStatus.PENDING)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    order: Mapped[int] = mapped_column(Integer, default=0)

    project = relationship("Project", back_populates="tasks")
    prd = relationship("PRD", back_populates="tasks")
    commits = relationship("Commit", back_populates="task")

    __table_args__ = (
        CheckConstraint(
            status.in_([s.value for s in TaskStatus]),
            name="ck_task_status",
        ),
    )
