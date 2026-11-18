import pytest

from app.github_client import GitHubClient


@pytest.mark.asyncio
async def test_github_client_mock(mocker):
    mock_response_repo = mocker.Mock()
    mock_response_repo.status_code = 200
    mock_response_repo.json.return_value = {
        "full_name": "octocat/Hello-World",
        "default_branch": "master",
        "html_url": "https://github.com/octocat/Hello-World",
    }

    mock_response_commit = mocker.Mock()
    mock_response_commit.status_code = 200
    mock_response_commit.json.return_value = {
        "sha": "7fd1a60b01f91b314f59955a4e4d4e80bdaedf11",
        "commit": {"message": "Initial commit"},
        "html_url": "https://github.com/octocat/Hello-World/commit/7fd1a60b",
    }

    mock_response_runs = mocker.Mock()
    mock_response_runs.status_code = 200
    mock_response_runs.json.return_value = {
        "workflow_runs": [
            {
                "status": "completed",
                "conclusion": "success",
                "html_url": "https://github.com/octocat/Hello-World/actions/runs/123",
            }
        ]
    }

    mocker.patch(
        "httpx.AsyncClient.get",
        side_effect=[mock_response_repo, mock_response_commit, mock_response_runs],
    )

    client = GitHubClient(token=None)
    status = await client.get_repository_status("octocat", "Hello-World")

    assert status["full_name"] == "octocat/Hello-World"
    assert status["default_branch"] == "master"
    assert status["commit_sha"] == "7fd1a60"
    assert status["commit_message"] == "Initial commit"
    assert status["workflow_status"] == "completed"
    assert status["workflow_conclusion"] == "success"


@pytest.mark.parametrize(
    "code,exception", [(404, ValueError), (403, RuntimeError), (429, RuntimeError)]
)
async def test_github_denial(monkeypatch, code, exception):
    from unittest.mock import AsyncMock

    import httpx

    monkeypatch.setattr(httpx.AsyncClient, "get", AsyncMock(return_value=httpx.Response(code)))
    with pytest.raises(exception):
        await GitHubClient().get_repository("example", "private")
