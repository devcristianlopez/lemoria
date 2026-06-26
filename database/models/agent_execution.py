import uuid
from sqlalchemy import String, Text, ForeignKey, Integer, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin
from database.enums import ExecutionStatus


class AgentExecution(TimestampMixin, Base):
    __tablename__ = "agent_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False)
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=ExecutionStatus.PENDING)
    input_data: Mapped[str] = mapped_column(Text, nullable=True)
    output_data: Mapped[str] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    error: Mapped[str] = mapped_column(Text, nullable=True)

    agent = relationship("Agent", back_populates="executions")

    __table_args__ = (
        CheckConstraint(
            status.in_([s.value for s in ExecutionStatus]),
            name="ck_execution_status",
        ),
    )
