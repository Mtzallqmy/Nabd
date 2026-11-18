import re
from urllib.parse import quote

import httpx

from app.config import settings

OWNER_PATTERN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?\Z")
REPO_PATTERN = re.compile(r"[A-Za-z0-9_.-]{1,100}\Z")


def validate_repository(owner: str, repo: str) -> tuple[str, str]:
    owner, repo = owner.strip(), repo.strip()
    if not OWNER_PATTERN.fullmatch(owner) or (
        repo in {".", ".."} or not REPO_PATTERN.fullmatch(repo)
    ):
        raise ValueError("اسم المالك أو المستودع غير صالح. استخدم owner/repository.")
    return owner, repo


class GitHubClient:
    BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None):
        self.token = (
            token
            if token is not None
            else (settings.github_token.get_secret_value() if settings.github_token else None)
        )

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "NABD-Command-Center-Bot",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def get_repository(self, owner: str, repo: str, *, client=None) -> dict:
        owner, repo = validate_repository(owner, repo)
        if client is None:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=False) as session:
                return await self.get_repository(owner, repo, client=session)
        response = await client.get(
            f"{self.BASE_URL}/repos/{owner}/{repo}", headers=self._get_headers()
        )
        if response.status_code == 404:
            raise ValueError(f"المستودع {owner}/{repo} غير موجود أو غير متاح.")
        if response.status_code in (403, 429):
            raise RuntimeError("تعذر الوصول إلى GitHub: الصلاحيات أو حد الطلبات.")
        response.raise_for_status()
        return response.json()

    async def get_repository_status(self, owner: str, repo: str) -> dict:
        owner, repo = validate_repository(owner, repo)
        headers = self._get_headers()
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=False) as client:
            repo_data = await self.get_repository(owner, repo, client=client)

            default_branch = repo_data.get("default_branch") or "main"
            commit_sha, commit_message, commit_url = None, None, None
            commit_error = None
            try:
                commit_resp = await client.get(
                    f"{self.BASE_URL}/repos/{owner}/{repo}/commits/{quote(default_branch, safe='')}",
                    headers=headers,
                )
                if commit_resp.status_code == 200:
                    commit_data = commit_resp.json()
                    commit_sha = commit_data.get("sha", "")[:7]
                    commit_message = (commit_data.get("commit", {}).get("message") or "").partition(
                        "\n"
                    )[0] or None
                    commit_url = commit_data.get("html_url")
                else:
                    commit_error = f"HTTP {commit_resp.status_code}"
            except (httpx.HTTPError, KeyError, ValueError, IndexError) as exc:
                commit_error = type(exc).__name__

            workflow_status = "not_available"
            workflow_conclusion = None
            workflow_url = None
            workflow_error = None
            try:
                workflow_resp = await client.get(
                    f"{self.BASE_URL}/repos/{owner}/{repo}/actions/runs?per_page=1",
                    headers=headers,
                )
                if workflow_resp.status_code == 200:
                    runs = workflow_resp.json().get("workflow_runs", [])
                    if runs:
                        run = runs[0]
                        workflow_status = run.get("status", "unknown")
                        workflow_conclusion = run.get("conclusion")
                        workflow_url = run.get("html_url")
                    else:
                        workflow_status = "no_runs"
                else:
                    workflow_error = f"HTTP {workflow_resp.status_code}"
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                workflow_error = type(exc).__name__

            return {
                "full_name": repo_data.get("full_name", f"{owner}/{repo}"),
                "default_branch": default_branch,
                "repo_url": repo_data.get("html_url", f"https://github.com/{owner}/{repo}"),
                "commit_sha": commit_sha,
                "commit_message": commit_message,
                "commit_url": commit_url,
                "commit_error": commit_error,
                "workflow_status": workflow_status,
                "workflow_conclusion": workflow_conclusion,
                "workflow_url": workflow_url,
                "workflow_error": workflow_error,
            }
