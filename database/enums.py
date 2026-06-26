"""Type-safe status enums for all Lemoria models."""

from enum import Enum


class PRDStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"

    def __str__(self) -> str:
        return self.value


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    def __str__(self) -> str:
        return self.value


class FlowStepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

    def __str__(self) -> str:
        return self.value


class DecisionStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"

    def __str__(self) -> str:
        return self.value


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

    def __str__(self) -> str:
        return self.value


class SpecStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    APPROVED = "approved"
    SUPERSEDED = "superseded"

    def __str__(self) -> str:
        return self.value


class CommitFileStatus(str, Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"

    def __str__(self) -> str:
        return self.value


class SolutionOutcome(str, Enum):
    UNKNOWN = "unknown"
    SUCCESSFUL = "successful"
    UNSUCCESSFUL = "unsuccessful"
    PARTIAL = "partial"

    def __str__(self) -> str:
        return self.value
