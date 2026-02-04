# Devin GitHub Issues Integration

A CLI tool to integrate Devin with GitHub Issues for automated issue scoping and execution.

## Features

This integration provides three main capabilities:

1. **View Issues**: List and view GitHub issues from your repository
2. **Scope Issues**: Trigger a Devin session to analyze an issue and provide a confidence score and action plan
3. **Execute Issues**: Trigger a Devin session to implement the solution and create a pull request

## Installation

From the repository root:

```bash
poetry install
```

Then run commands with:

```bash
poetry run devin-issues <command>
```

Or activate the virtual environment first:

```bash
poetry shell
devin-issues <command>
```

## Configuration

Set the following environment variables:

```bash
export DEVIN_API_KEY="your-devin-api-key"
export GITHUB_TOKEN="your-github-token"
export GITHUB_REPO="owner/repo"  # Optional, defaults to luigisambuy/quickstart
```

You can get your Devin API key from [https://app.devin.ai/settings/api-keys](https://app.devin.ai/settings/api-keys).

Create a GitHub personal access token at [https://github.com/settings/tokens](https://github.com/settings/tokens) with `repo` scope.

## Usage

### List Issues

```bash
# List all open issues
devin-issues list

# List with filters
devin-issues list --state open --limit 10 --verbose

# Filter by labels
devin-issues list --labels bug,enhancement
```

### View Issue Details

```bash
devin-issues show 42
```

### Scope an Issue

Trigger a Devin session to analyze an issue and provide:
- Confidence score (0-100)
- Action plan with specific steps
- Estimated complexity (low/medium/high)
- Potential blockers
- Files to modify

```bash
# Start scoping session (returns immediately)
devin-issues scope 42

# Wait for scoping to complete
devin-issues scope 42 --wait

# Scope an issue from an external repository
devin-issues scope 35656 --source-repo facebook/react
```

### Execute an Issue

Trigger a Devin session to implement the solution:

```bash
# Start execution session (returns immediately)
devin-issues execute 42

# Wait for execution to complete
devin-issues execute 42 --wait
```

### Execute with Private Repository Workflow

For working on issues from public repositories while keeping your work private:

```bash
# Work on an issue from a public repo, but create PR on your private repo
devin-issues execute 42 --source-repo facebook/react --private-repo myuser/my-private-repo
```

This workflow:
1. Clones the public source repository (e.g., `facebook/react`)
2. Creates a feature branch for the fix
3. Pushes the branch to your private repository
4. Creates a PR on your private repository (not the public one)

This is useful when you want to:
- Work on open source issues privately before contributing upstream
- Test fixes in your own environment first
- Keep your work-in-progress hidden until ready

### Check Session Status

```bash
devin-issues status <session-id>
```

## Example Workflow

1. **List issues** to find work to do:
   ```bash
   devin-issues list --state open
   ```

2. **View issue details** to understand the problem:
   ```bash
   devin-issues show 42
   ```

3. **Scope the issue** to get Devin's analysis:
   ```bash
   devin-issues scope 42 --wait
   ```

4. **Review the confidence score** and action plan. If confidence is high enough:
   ```bash
   devin-issues execute 42
   ```

5. **Monitor progress** using the session URL or status command:
   ```bash
   devin-issues status abc123-session-id
   ```

## Confidence Score Guide

The confidence score indicates how confident Devin is about solving the issue:

- **90-100**: Very confident - straightforward issue with clear solution
- **70-89**: Confident - some complexity but manageable
- **50-69**: Moderate confidence - significant complexity or unknowns
- **30-49**: Low confidence - major blockers or unclear requirements
- **0-29**: Very low confidence - likely cannot complete without more information

## API Reference

### Python API

You can also use the integration programmatically:

```python
from devin_github_integration.config import Config
from devin_github_integration.github_client import GitHubClient
from devin_github_integration.devin_client import DevinClient

# Initialize
config = Config.from_env()
github = GitHubClient(config)
devin = DevinClient(config)

# List issues
issues = github.list_issues(limit=10)

# Scope an issue
issue = github.get_issue(42)
scoping_result = devin.trigger_scoping_session(issue, wait=True)
print(f"Confidence: {scoping_result.confidence_score}%")

# Execute an issue
execution_result = devin.trigger_execution_session(issue, scoping_result=scoping_result)
print(f"Session URL: {execution_result.session_url}")
```

## License

MIT License
