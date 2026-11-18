import pytest
from sqlalchemy import select

from app.models import ActivityModel
from app.services import ProjectService


@pytest.mark.asyncio
async def test_project_crud(db_session, mocker):
    mocker.patch(
        "app.github_client.GitHubClient.get_repository",
        return_value={
            "full_name": "testowner/testrepo",
            "default_branch": "main",
            "repo_url": "https://github.com/testowner/testrepo",
            "commit_sha": "abcdef1",
            "commit_message": "Test commit",
            "commit_url": None,
            "workflow_status": "completed",
            "workflow_conclusion": "success",
            "workflow_url": None,
        },
    )

    project = await ProjectService.add_project(db_session, "testowner", "testrepo", 12345)
    assert project.owner == "testowner"
    assert project.repository == "testrepo"
    assert project.registered_by == 12345

    projects = await ProjectService.list_projects(db_session)
    assert len(projects) == 1

    removed = await ProjectService.remove_project_by_id(db_session, project.id, 12345)
    assert removed is True

    projects_after = await ProjectService.list_projects(db_session)
    assert len(projects_after) == 0

    activities = list(
        (await db_session.scalars(select(ActivityModel).order_by(ActivityModel.id))).all()
    )
    assert [activity.action for activity in activities] == ["added", "removed"]
    assert {activity.actor_id for activity in activities} == {12345}


async def test_duplicate_slug_and_large_telegram_id(db_session, mocker):
    mocker.patch("app.github_client.GitHubClient.get_repository", return_value={})
    telegram_id = 5_000_000_000
    await ProjectService.add_project(db_session, "Owner", "Repo", telegram_id)
    with pytest.raises(ValueError, match="مسجل"):
        await ProjectService.add_project(db_session, "owner", "repo", telegram_id)
    assert (await ProjectService.list_projects(db_session))[0].registered_by == telegram_id
    assert len(await ProjectService.list_projects(db_session)) == 1
