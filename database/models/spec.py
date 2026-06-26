import uuid
from sqlalchemy import String, Text, ForeignKey, Integer, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin
from database.enums import SpecStatus


class Spec(TimestampMixin, Base):
    __tablename__ = "specs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prd_id: Mapped[str] = mapped_column(String(36), ForeignKey("prds.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=SpecStatus.DRAFT)
    order: Mapped[int] = mapped_column(Integer, default=0)

    prd = relationship("PRD", back_populates="specs")

    __table_args__ = (
        CheckConstraint(
            status.in_([s.value for s in SpecStatus]),
            name="ck_spec_status",
        ),
    )
