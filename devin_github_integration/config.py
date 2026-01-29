"""Configuration management for Devin GitHub Integration."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Configuration settings for the integration."""

    devin_api_key: str
    github_token: str
    github_repo: str
    devin_api_base: str = "https://api.devin.ai/v1"
    github_api_base: str = "https://api.github.com"

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        devin_api_key = os.environ.get("DEVIN_API_KEY", "")
        github_token = os.environ.get("GITHUB_TOKEN", "")
        github_repo = os.environ.get("GITHUB_REPO", "luigisambuy/quickstart")

        if not devin_api_key:
            raise ValueError(
                "DEVIN_API_KEY environment variable is required. "
                "Get your API key from https://app.devin.ai/settings/api-keys"
            )

        if not github_token:
            raise ValueError(
                "GITHUB_TOKEN environment variable is required. "
                "Create a personal access token at https://github.com/settings/tokens"
            )

        return cls(
            devin_api_key=devin_api_key,
            github_token=github_token,
            github_repo=github_repo,
        )

    @classmethod
    def from_args(
        cls,
        devin_api_key: Optional[str] = None,
        github_token: Optional[str] = None,
        github_repo: Optional[str] = None,
    ) -> "Config":
        """Load configuration from arguments, falling back to environment variables."""
        return cls(
            devin_api_key=devin_api_key or os.environ.get("DEVIN_API_KEY", ""),
            github_token=github_token or os.environ.get("GITHUB_TOKEN", ""),
            github_repo=github_repo or os.environ.get("GITHUB_REPO", "luigisambuy/quickstart"),
        )
