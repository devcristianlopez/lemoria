import uuid
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    repo_url: Mapped[str] = mapped_column(String(1024), nullable=True)
    repo_path: Mapped[str] = mapped_column(String(1024), nullable=True)
    active: Mapped[bool] = mapped_column(default=True)

    conversations = relationship("Conversation", back_populates="project")
    prds = relationship("PRD", back_populates="project")
    tasks = relationship("Task", back_populates="project")
    decisions = relationship("Decision", back_populates="project")
    contexts = relationship("Context", back_populates="project")
