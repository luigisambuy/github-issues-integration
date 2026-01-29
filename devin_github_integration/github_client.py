"""GitHub API client for fetching issues."""

import requests
from typing import List, Optional

from .config import Config
from .models import GitHubIssue, IssueState


class GitHubClient:
    """Client for interacting with GitHub API."""

    def __init__(self, config: Config):
        """Initialize the GitHub client."""
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {config.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def _get_repo_url(self) -> str:
        """Get the base URL for the repository."""
        return f"{self.config.github_api_base}/repos/{self.config.github_repo}"

    def list_issues(
        self,
        state: Optional[IssueState] = None,
        labels: Optional[List[str]] = None,
        limit: int = 30,
    ) -> List[GitHubIssue]:
        """List issues from the repository.

        Args:
            state: Filter by issue state (open, closed, or None for all)
            labels: Filter by labels
            limit: Maximum number of issues to return

        Returns:
            List of GitHubIssue objects
        """
        url = f"{self._get_repo_url()}/issues"
        params = {"per_page": min(limit, 100)}

        if state:
            params["state"] = state.value
        else:
            params["state"] = "all"

        if labels:
            params["labels"] = ",".join(labels)

        response = self.session.get(url, params=params)
        response.raise_for_status()

        issues = []
        for item in response.json():
            if "pull_request" not in item:
                issues.append(GitHubIssue.from_api_response(item))

        return issues[:limit]

    def get_issue(self, issue_number: int) -> GitHubIssue:
        """Get a specific issue by number.

        Args:
            issue_number: The issue number

        Returns:
            GitHubIssue object

        Raises:
            requests.HTTPError: If the issue is not found
        """
        url = f"{self._get_repo_url()}/issues/{issue_number}"
        response = self.session.get(url)
        response.raise_for_status()
        return GitHubIssue.from_api_response(response.json())

    def get_issue_comments(self, issue_number: int) -> List[dict]:
        """Get comments for a specific issue.

        Args:
            issue_number: The issue number

        Returns:
            List of comment dictionaries
        """
        url = f"{self._get_repo_url()}/issues/{issue_number}/comments"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
