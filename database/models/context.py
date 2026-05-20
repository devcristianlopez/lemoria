import uuid
from sqlalchemy import String, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin


class Context(TimestampMixin, Base):
    __tablename__ = "contexts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    parent_id: Mapped[str] = mapped_column(String(36), ForeignKey("contexts.id"), nullable=True)
    level: Mapped[str] = mapped_column(String(32), default="global")
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)

    project = relationship("Project", back_populates="contexts")
    children = relationship("Context", backref="parent", remote_side=[id])
