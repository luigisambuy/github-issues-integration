#!/usr/bin/env python3
"""CLI interface for Devin GitHub Issues Integration."""

import argparse
import sys

from .config import Config
from .github_client import GitHubClient
from .devin_client import DevinClient
from .models import IssueState


def print_issue(issue, verbose: bool = False):
    """Print a formatted issue."""
    state_icon = "[OPEN]" if issue.state == IssueState.OPEN else "[CLOSED]"
    labels = f" [{', '.join(issue.labels)}]" if issue.labels else ""

    print(f"#{issue.number} {state_icon} {issue.title}{labels}")

    if verbose:
        print(f"  URL: {issue.url}")
        print(f"  Created: {issue.created_at.strftime('%Y-%m-%d %H:%M')}")
        if issue.assignees:
            print(f"  Assignees: {', '.join(issue.assignees)}")
        if issue.body:
            body_preview = issue.body[:200].replace("\n", " ")
            if len(issue.body) > 200:
                body_preview += "..."
            print(f"  Description: {body_preview}")
        print()


def print_scoping_result(result):
    """Print a formatted scoping result."""
    print("\n" + "=" * 60)
    print(f"SCOPING RESULT - Issue #{result.issue_number}")
    print("=" * 60)
    print(f"\nSession ID: {result.session_id}")
    print(f"Session URL: {result.session_url}")

    if result.confidence_score > 0:
        confidence_bar = "#" * (result.confidence_score // 5) + "-" * (20 - result.confidence_score // 5)
        print(f"\nConfidence Score: {result.confidence_score}% [{confidence_bar}]")
        print(f"Estimated Complexity: {result.estimated_complexity.value.upper()}")

        if result.summary:
            print(f"\nSummary: {result.summary}")

        if result.action_plan:
            print("\nAction Plan:")
            for i, step in enumerate(result.action_plan, 1):
                print(f"  {i}. {step}")

        if result.files_to_modify:
            print(f"\nFiles to Modify: {', '.join(result.files_to_modify)}")

        if result.potential_blockers:
            print("\nPotential Blockers:")
            for blocker in result.potential_blockers:
                print(f"  - {blocker}")
    else:
        print("\nSession started. Results will be available once Devin completes the analysis.")
        print("Use 'devin-issues status <session_id>' to check progress.")

    print()


def print_execution_result(result):
    """Print a formatted execution result."""
    print("\n" + "=" * 60)
    print(f"EXECUTION RESULT - Issue #{result.issue_number}")
    print("=" * 60)
    print(f"\nSession ID: {result.session_id}")
    print(f"Session URL: {result.session_url}")

    if result.status != "unknown":
        print(f"Status: {result.status.upper()}")

        if result.completed_steps:
            print("\nCompleted Steps:")
            for step in result.completed_steps:
                print(f"  - {step}")

        if result.pr_url:
            print(f"\nPull Request: {result.pr_url}")

        if result.issues_encountered:
            print("\nIssues Encountered:")
            for issue in result.issues_encountered:
                print(f"  - {issue}")
    else:
        print("\nSession started. Results will be available once Devin completes the work.")
        print("Use 'devin-issues status <session_id>' to check progress.")

    print()


def cmd_list(args, config: Config):
    """List GitHub issues."""
    github = GitHubClient(config)

    state = None
    if args.state:
        state = IssueState(args.state)

    labels = args.labels.split(",") if args.labels else None

    try:
        issues = github.list_issues(state=state, labels=labels, limit=args.limit)

        if not issues:
            print("No issues found.")
            return

        print(f"\nFound {len(issues)} issue(s) in {config.github_repo}:\n")
        for issue in issues:
            print_issue(issue, verbose=args.verbose)

    except Exception as e:
        print(f"Error fetching issues: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_show(args, config: Config):
    """Show details of a specific issue."""
    github = GitHubClient(config)

    try:
        issue = github.get_issue(args.issue_number)
        print(f"\n{'=' * 60}")
        print(f"Issue #{issue.number}: {issue.title}")
        print("=" * 60)
        print(f"\nState: {issue.state.value.upper()}")
        print(f"URL: {issue.url}")
        print(f"Created: {issue.created_at.strftime('%Y-%m-%d %H:%M')}")
        print(f"Updated: {issue.updated_at.strftime('%Y-%m-%d %H:%M')}")

        if issue.labels:
            print(f"Labels: {', '.join(issue.labels)}")
        if issue.assignees:
            print(f"Assignees: {', '.join(issue.assignees)}")

        print(f"\nDescription:\n{'-' * 40}")
        print(issue.body if issue.body else "(No description)")
        print()

    except Exception as e:
        print(f"Error fetching issue: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_scope(args, config: Config):
    """Trigger a scoping session for an issue."""
    source_repo = getattr(args, 'source_repo', None)

    if source_repo:
        source_config = Config.from_args(
            devin_api_key=config.devin_api_key,
            github_token=config.github_token,
            github_repo=source_repo,
        )
        github = GitHubClient(source_config)
    else:
        github = GitHubClient(config)

    devin = DevinClient(config)

    try:
        issue = github.get_issue(args.issue_number)
        repo_name = source_repo or config.github_repo
        print(f"\nStarting scoping session for Issue #{issue.number}: {issue.title}")
        print(f"Repository: {repo_name}")
        print("This may take a few minutes...")

        result = devin.trigger_scoping_session(issue, wait=args.wait)
        print_scoping_result(result)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_execute(args, config: Config):
    """Trigger an execution session for an issue."""
    source_repo = getattr(args, 'source_repo', None)
    private_repo = getattr(args, 'private_repo', None)

    if source_repo:
        source_config = Config.from_args(
            devin_api_key=config.devin_api_key,
            github_token=config.github_token,
            github_repo=source_repo,
        )
        github = GitHubClient(source_config)
    else:
        github = GitHubClient(config)

    devin = DevinClient(config)

    try:
        issue = github.get_issue(args.issue_number)

        if private_repo:
            actual_source = source_repo or config.github_repo
            print(f"\nStarting private repo execution for Issue #{issue.number}: {issue.title}")
            print(f"Source: {actual_source} -> Private: {private_repo}")
            print("This may take a while...")

            result = devin.trigger_private_repo_execution(
                issue=issue,
                source_repo=actual_source,
                private_repo=private_repo,
                wait=args.wait,
            )
        else:
            print(f"\nStarting execution session for Issue #{issue.number}: {issue.title}")
            print("This may take a while...")

            result = devin.trigger_execution_session(issue, wait=args.wait)

        print_execution_result(result)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_status(args, config: Config):
    """Check the status of a Devin session."""
    devin = DevinClient(config)

    try:
        session = devin.get_session(args.session_id)

        print(f"\n{'=' * 60}")
        print(f"Session Status: {args.session_id}")
        print("=" * 60)
        print(f"\nStatus: {session.status.value.upper()}")
        print(f"URL: {session.url}")

        if session.structured_output:
            print("\nStructured Output:")
            import json
            print(json.dumps(session.structured_output, indent=2))
        print()

    except Exception as e:
        print(f"Error fetching session: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="devin-issues",
        description="Devin GitHub Issues Integration - Automate issue scoping and execution with Devin",
    )

    parser.add_argument(
        "--repo",
        "-r",
        help="GitHub repository (owner/repo format)",
        default=None,
    )
    parser.add_argument(
        "--devin-key",
        help="Devin API key (or set DEVIN_API_KEY env var)",
        default=None,
    )
    parser.add_argument(
        "--github-token",
        help="GitHub token (or set GITHUB_TOKEN env var)",
        default=None,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List GitHub issues")
    list_parser.add_argument(
        "--state",
        "-s",
        choices=["open", "closed"],
        help="Filter by issue state",
    )
    list_parser.add_argument(
        "--labels",
        "-l",
        help="Filter by labels (comma-separated)",
    )
    list_parser.add_argument(
        "--limit",
        "-n",
        type=int,
        default=30,
        help="Maximum number of issues to show (default: 30)",
    )
    list_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed issue information",
    )

    # Show command
    show_parser = subparsers.add_parser("show", help="Show details of a specific issue")
    show_parser.add_argument("issue_number", type=int, help="Issue number")

    # Scope command
    scope_parser = subparsers.add_parser(
        "scope", help="Trigger a Devin session to scope an issue"
    )
    scope_parser.add_argument("issue_number", type=int, help="Issue number to scope")
    scope_parser.add_argument(
        "--wait",
        "-w",
        action="store_true",
        help="Wait for the session to complete",
    )
    scope_parser.add_argument(
        "--source-repo",
        help="Source repository for the issue (owner/repo format). Use to scope issues from external repos.",
    )

    # Execute command
    execute_parser = subparsers.add_parser(
        "execute", help="Trigger a Devin session to complete an issue"
    )
    execute_parser.add_argument("issue_number", type=int, help="Issue number to execute")
    execute_parser.add_argument(
        "--wait",
        "-w",
        action="store_true",
        help="Wait for the session to complete",
    )
    execute_parser.add_argument(
        "--source-repo",
        help="Source repository for the issue (owner/repo format). Use with --private-repo for private workflow.",
    )
    execute_parser.add_argument(
        "--private-repo",
        help="Private repository to push changes to (owner/repo format). Creates PR on private repo instead of source.",
    )

    # Status command
    status_parser = subparsers.add_parser(
        "status", help="Check the status of a Devin session"
    )
    status_parser.add_argument("session_id", help="Devin session ID")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    try:
        config = Config.from_args(
            devin_api_key=args.devin_key,
            github_token=args.github_token,
            github_repo=args.repo,
        )
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    commands = {
        "list": cmd_list,
        "show": cmd_show,
        "scope": cmd_scope,
        "execute": cmd_execute,
        "status": cmd_status,
    }

    commands[args.command](args, config)


if __name__ == "__main__":
    main()
