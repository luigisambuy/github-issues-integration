"""Devin API client for triggering and managing sessions."""

import time
import requests
from typing import Optional

from .config import Config
from .models import DevinSession, GitHubIssue, ScopingResult, ExecutionResult, SessionStatus


class DevinClient:
    """Client for interacting with Devin API."""

    def __init__(self, config: Config):
        """Initialize the Devin client."""
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {config.devin_api_key}",
                "Content-Type": "application/json",
            }
        )

    def _create_session(self, prompt: str, title: Optional[str] = None) -> dict:
        """Create a new Devin session.

        Args:
            prompt: The prompt for Devin
            title: Optional title for the session

        Returns:
            Session creation response
        """
        url = f"{self.config.devin_api_base}/sessions"
        payload = {"prompt": prompt}
        if title:
            payload["title"] = title

        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def get_session(self, session_id: str) -> DevinSession:
        """Get session details.

        Args:
            session_id: The session ID

        Returns:
            DevinSession object
        """
        url = f"{self.config.devin_api_base}/sessions/{session_id}"
        response = self.session.get(url)
        response.raise_for_status()
        data = response.json()
        data["session_id"] = session_id
        return DevinSession.from_api_response(data)

    def wait_for_session(
        self, session_id: str, poll_interval: int = 15, timeout: int = 600
    ) -> DevinSession:
        """Wait for a session to complete.

        Args:
            session_id: The session ID
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait

        Returns:
            Final DevinSession object
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            session = self.get_session(session_id)
            if session.status in [SessionStatus.BLOCKED, SessionStatus.STOPPED]:
                return session
            time.sleep(poll_interval)

        return self.get_session(session_id)

    def trigger_scoping_session(
        self, issue: GitHubIssue, wait: bool = False
    ) -> ScopingResult:
        """Trigger a scoping session for an issue.

        Args:
            issue: The GitHub issue to scope
            wait: Whether to wait for the session to complete

        Returns:
            ScopingResult object
        """
        structured_output_schema = """{
    "confidence_score": 85,
    "action_plan": ["Step 1: ...", "Step 2: ..."],
    "estimated_complexity": "medium",
    "potential_blockers": ["Blocker 1", "Blocker 2"],
    "files_to_modify": ["file1.py", "file2.py"],
    "summary": "Brief summary of the issue and approach"
}"""

        prompt = f"""Analyze the following GitHub issue and provide a scoping assessment.

## Issue #{issue.number}: {issue.title}

{issue.body}

---

## Your Task

1. Analyze this issue thoroughly
2. Determine how confident you are (0-100) that you can solve this issue
3. Create a detailed action plan with specific steps
4. Identify the complexity level (low/medium/high)
5. List any potential blockers or dependencies
6. Identify which files would need to be modified

Please update the structured output with your analysis in this format:
{structured_output_schema}

Important: Update the structured output immediately with your findings. The confidence_score should reflect:
- 90-100: Very confident, straightforward issue with clear solution
- 70-89: Confident, some complexity but manageable
- 50-69: Moderate confidence, significant complexity or unknowns
- 30-49: Low confidence, major blockers or unclear requirements
- 0-29: Very low confidence, likely cannot complete without more information

Repository: {self.config.github_repo}
Issue URL: {issue.url}
"""

        title = f"Scoping Issue #{issue.number}: {issue.title[:50]}"
        response = self._create_session(prompt, title)

        session_id = response["session_id"]
        session_url = response["url"]

        if wait:
            final_session = self.wait_for_session(session_id)
            output = final_session.structured_output or {}
        else:
            output = {}

        return ScopingResult.from_structured_output(
            issue_number=issue.number,
            session_id=session_id,
            session_url=session_url,
            output=output,
        )

    def trigger_execution_session(
        self,
        issue: GitHubIssue,
        scoping_result: Optional[ScopingResult] = None,
        wait: bool = False,
    ) -> ExecutionResult:
        """Trigger an execution session to complete an issue.

        Args:
            issue: The GitHub issue to complete
            scoping_result: Optional scoping result to use as context
            wait: Whether to wait for the session to complete

        Returns:
            ExecutionResult object
        """
        structured_output_schema = """{
    "status": "in_progress",
    "completed_steps": ["Step 1 completed", "Step 2 completed"],
    "pr_url": "https://github.com/owner/repo/pull/123",
    "issues_encountered": ["Issue 1", "Issue 2"]
}"""

        action_plan_context = ""
        if scoping_result and scoping_result.action_plan:
            action_plan_context = f"""
## Action Plan from Scoping

The following action plan was created during scoping (confidence: {scoping_result.confidence_score}%):

{chr(10).join(f"- {step}" for step in scoping_result.action_plan)}

Files to modify: {', '.join(scoping_result.files_to_modify) if scoping_result.files_to_modify else 'TBD'}

Potential blockers: {', '.join(scoping_result.potential_blockers) if scoping_result.potential_blockers else 'None identified'}
"""

        prompt = f"""Complete the following GitHub issue by implementing the required changes and creating a pull request.

## Issue #{issue.number}: {issue.title}

{issue.body}
{action_plan_context}
---

## Your Task

1. Clone the repository: {self.config.github_repo}
2. Implement the required changes following the action plan
3. Write tests if applicable
4. Create a pull request with your changes
5. Update the structured output with your progress

Please update the structured output as you work in this format:
{structured_output_schema}

Important: Update the structured output immediately whenever you:
- Complete a step
- Encounter an issue
- Create a PR

Repository: {self.config.github_repo}
Issue URL: {issue.url}
"""

        title = f"Executing Issue #{issue.number}: {issue.title[:50]}"
        response = self._create_session(prompt, title)

        session_id = response["session_id"]
        session_url = response["url"]

        if wait:
            final_session = self.wait_for_session(session_id)
            output = final_session.structured_output or {}
        else:
            output = {}

        return ExecutionResult.from_structured_output(
            issue_number=issue.number,
            session_id=session_id,
            session_url=session_url,
            output=output,
        )

    def trigger_private_repo_execution(
        self,
        issue: GitHubIssue,
        source_repo: str,
        private_repo: str,
        scoping_result: Optional[ScopingResult] = None,
        wait: bool = False,
    ) -> ExecutionResult:
        """Trigger an execution session that works on a private repo.

        This workflow:
        1. Clones the public source repo
        2. Pushes to the user's private repo
        3. Creates a branch and implements the fix
        4. Creates a PR on the private repo (not the public source)

        Args:
            issue: The GitHub issue to complete
            source_repo: The public source repository (owner/repo format)
            private_repo: The private repository to push to (owner/repo format)
            scoping_result: Optional scoping result to use as context
            wait: Whether to wait for the session to complete

        Returns:
            ExecutionResult object
        """
        structured_output_schema = """{
    "status": "in_progress",
    "completed_steps": ["Step 1 completed", "Step 2 completed"],
    "pr_url": "https://github.com/owner/repo/pull/123",
    "issues_encountered": ["Issue 1", "Issue 2"]
}"""

        action_plan_context = ""
        if scoping_result and scoping_result.action_plan:
            action_plan_context = f"""
## Action Plan from Scoping

The following action plan was created during scoping (confidence: {scoping_result.confidence_score}%):

{chr(10).join(f"- {step}" for step in scoping_result.action_plan)}

Files to modify: {', '.join(scoping_result.files_to_modify) if scoping_result.files_to_modify else 'TBD'}

Potential blockers: {', '.join(scoping_result.potential_blockers) if scoping_result.potential_blockers else 'None identified'}
"""

        prompt = f"""Complete the following GitHub issue by implementing the required changes in a PRIVATE repository workflow.

## Issue #{issue.number}: {issue.title}

{issue.body}
{action_plan_context}
---

## IMPORTANT: Private Repository Workflow

You must follow this specific workflow to keep the work private:

1. **Clone the public source repository**:
   ```bash
   git clone https://github.com/{source_repo}.git
   cd $(basename {source_repo})
   ```

2. **Add the private repository as a remote**:
   ```bash
   git remote add private https://github.com/{private_repo}.git
   ```

3. **Create a feature branch**:
   ```bash
   git checkout -b fix/issue-{issue.number}
   ```

4. **Implement the required changes** following the action plan

5. **Push to the PRIVATE repository** (not the public source):
   ```bash
   git push private fix/issue-{issue.number}
   ```

6. **Create a pull request on the PRIVATE repository** ({private_repo})
   - The PR should be created on {private_repo}, NOT on {source_repo}
   - This keeps the work private until the user is ready to contribute upstream

## Your Task

1. Follow the private repository workflow above exactly
2. Implement the fix for the issue
3. Write tests if applicable
4. Create a PR on the PRIVATE repo: {private_repo}
5. Update the structured output with your progress

Please update the structured output as you work in this format:
{structured_output_schema}

Important: Update the structured output immediately whenever you:
- Complete a step
- Encounter an issue
- Create a PR

Source Repository (public): {source_repo}
Private Repository (for PR): {private_repo}
Issue URL: {issue.url}
"""

        title = f"[Private] Issue #{issue.number}: {issue.title[:40]}"
        response = self._create_session(prompt, title)

        session_id = response["session_id"]
        session_url = response["url"]

        if wait:
            final_session = self.wait_for_session(session_id)
            output = final_session.structured_output or {}
        else:
            output = {}

        return ExecutionResult.from_structured_output(
            issue_number=issue.number,
            session_id=session_id,
            session_url=session_url,
            output=output,
        )

    def send_message(self, session_id: str, message: str) -> dict:
        """Send a message to an active session.

        Args:
            session_id: The session ID
            message: The message to send

        Returns:
            API response
        """
        url = f"{self.config.devin_api_base}/sessions/{session_id}/message"
        response = self.session.post(url, json={"message": message})
        response.raise_for_status()
        return response.json()
