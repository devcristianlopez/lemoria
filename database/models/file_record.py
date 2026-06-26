import uuid
from sqlalchemy import String, Text, ForeignKey, Integer, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin
from database.enums import CommitFileStatus


class FileRecord(TimestampMixin, Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    commit_id: Mapped[str] = mapped_column(String(36), ForeignKey("commits.id"), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=CommitFileStatus.MODIFIED)
    additions: Mapped[int] = mapped_column(Integer, default=0)
    deletions: Mapped[int] = mapped_column(Integer, default=0)

    commit = relationship("Commit", back_populates="files")

    __table_args__ = (
        CheckConstraint(
            status.in_([s.value for s in CommitFileStatus]),
            name="ck_file_status",
        ),
    )
