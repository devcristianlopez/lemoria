import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin
from database.enums import FlowStepStatus


class FlowStep(TimestampMixin, Base):
    __tablename__ = "flow_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    flow_id: Mapped[str] = mapped_column(String(36), ForeignKey("prds.id"), nullable=False, index=True)
    step: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=FlowStepStatus.PENDING)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    output: Mapped[str] = mapped_column(Text, nullable=True)

    prd = relationship("PRD", backref="flow_steps")

    __table_args__ = (
        CheckConstraint(
            status.in_([s.value for s in FlowStepStatus]),
            name="ck_flow_step_status",
        ),
    )
