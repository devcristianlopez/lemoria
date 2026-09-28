import json
import uuid
from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin


class Agent(TimestampMixin, Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Declared in the agent's markdown frontmatter. NULL means "no model
    # declared", which opencode resolves by inheriting the invoking agent's
    # model -- see the "inherited" rendering in `lemoria agent status`.
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    variant: Mapped[str | None] = mapped_column(String(64), nullable=True)

    executions = relationship("AgentExecution", back_populates="agent")

    @property
    def config_dict(self) -> dict:
        """config is a JSON blob; an empty or corrupt value is not fatal."""
        if not self.config:
            return {}
        try:
            return json.loads(self.config)
        except (ValueError, TypeError):
            return {}
