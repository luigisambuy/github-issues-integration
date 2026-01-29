"""Data models for Devin GitHub Integration."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class IssueState(Enum):
    """GitHub issue state."""

    OPEN = "open"
    CLOSED = "closed"


class Complexity(Enum):
    """Issue complexity level."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SessionStatus(Enum):
    """Devin session status."""

    RUNNING = "running"
    BLOCKED = "blocked"
    STOPPED = "stopped"


@dataclass
class GitHubIssue:
    """Represents a GitHub issue."""

    number: int
    title: str
    body: str
    state: IssueState
    url: str
    created_at: datetime
    updated_at: datetime
    labels: List[str] = field(default_factory=list)
    assignees: List[str] = field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> "GitHubIssue":
        """Create a GitHubIssue from GitHub API response."""
        return cls(
            number=data["number"],
            title=data["title"],
            body=data.get("body") or "",
            state=IssueState(data["state"]),
            url=data["html_url"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
            labels=[label["name"] for label in data.get("labels", [])],
            assignees=[assignee["login"] for assignee in data.get("assignees", [])],
        )


@dataclass
class ScopingResult:
    """Result of a scoping session."""

    issue_number: int
    session_id: str
    session_url: str
    confidence_score: int
    action_plan: List[str]
    estimated_complexity: Complexity
    potential_blockers: List[str]
    files_to_modify: List[str]
    summary: str

    @classmethod
    def from_structured_output(
        cls, issue_number: int, session_id: str, session_url: str, output: dict
    ) -> "ScopingResult":
        """Create a ScopingResult from Devin structured output."""
        complexity_str = output.get("estimated_complexity", "medium").lower()
        try:
            complexity = Complexity(complexity_str)
        except ValueError:
            complexity = Complexity.MEDIUM

        return cls(
            issue_number=issue_number,
            session_id=session_id,
            session_url=session_url,
            confidence_score=output.get("confidence_score", 0),
            action_plan=output.get("action_plan", []),
            estimated_complexity=complexity,
            potential_blockers=output.get("potential_blockers", []),
            files_to_modify=output.get("files_to_modify", []),
            summary=output.get("summary", ""),
        )


@dataclass
class ExecutionResult:
    """Result of an execution session."""

    issue_number: int
    session_id: str
    session_url: str
    status: str
    completed_steps: List[str]
    pr_url: Optional[str]
    issues_encountered: List[str]

    @classmethod
    def from_structured_output(
        cls, issue_number: int, session_id: str, session_url: str, output: dict
    ) -> "ExecutionResult":
        """Create an ExecutionResult from Devin structured output."""
        return cls(
            issue_number=issue_number,
            session_id=session_id,
            session_url=session_url,
            status=output.get("status", "unknown"),
            completed_steps=output.get("completed_steps", []),
            pr_url=output.get("pr_url"),
            issues_encountered=output.get("issues_encountered", []),
        )


@dataclass
class DevinSession:
    """Represents a Devin session."""

    session_id: str
    url: str
    status: SessionStatus
    structured_output: Optional[dict] = None

    @classmethod
    def from_api_response(cls, data: dict) -> "DevinSession":
        """Create a DevinSession from Devin API response."""
        status_str = data.get("status_enum", "running").lower()
        try:
            status = SessionStatus(status_str)
        except ValueError:
            status = SessionStatus.RUNNING

        return cls(
            session_id=data["session_id"],
            url=data.get("url", ""),
            status=status,
            structured_output=data.get("structured_output"),
        )
