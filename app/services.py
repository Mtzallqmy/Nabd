from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.github_client import GitHubClient, validate_repository
from app.models import ActivityModel, ProjectModel, UserModel

PAGE_SIZE = 12


class ProjectService:
    @staticmethod
    def by_slug(owner: str, repository: str):
        return (
            func.lower(ProjectModel.owner) == owner.lower(),
            func.lower(ProjectModel.repository) == repository.lower(),
        )

    @staticmethod
    async def record_activity(session: AsyncSession, actor_id: int, action: str, project: str):
        insert = pg_insert if session.get_bind().dialect.name == "postgresql" else sqlite_insert
        await session.execute(insert(UserModel).values(id=actor_id).on_conflict_do_nothing())
        session.add(ActivityModel(actor_id=actor_id, action=action, project=project))

    @staticmethod
    async def add_project(session: AsyncSession, owner: str, repository: str, user_id: int):
        owner, repository = validate_repository(owner, repository)
        await GitHubClient().get_repository(owner, repository)
        project = ProjectModel(owner=owner, repository=repository, registered_by=user_id)
        try:
            await ProjectService.record_activity(session, user_id, "added", project.full_name)
            session.add(project)
            await session.commit()
        except IntegrityError:
            await session.rollback()
            existing = await session.scalar(
                select(ProjectModel.id).where(*ProjectService.by_slug(owner, repository))
            )
            if existing is not None:
                raise ValueError(f"المستودع {owner}/{repository} مسجل مسبقًا.") from None
            raise
        return project

    @staticmethod
    async def list_projects(session: AsyncSession, *, page: int = 0) -> list[ProjectModel]:
        result = await session.scalars(
            select(ProjectModel)
            .order_by(ProjectModel.id.desc())
            .offset(page * PAGE_SIZE)
            .limit(PAGE_SIZE + 1)
        )
        return list(result)

    @staticmethod
    async def get_project(session: AsyncSession, project_id: int) -> ProjectModel | None:
        return await session.get(ProjectModel, project_id)

    @staticmethod
    async def remove_project_by_id(session: AsyncSession, project_id: int, actor_id: int) -> bool:
        result = await session.execute(
            delete(ProjectModel)
            .where(ProjectModel.id == project_id)
            .returning(ProjectModel.owner, ProjectModel.repository)
        )
        deleted = result.one_or_none()
        if deleted is None:
            return False
        await ProjectService.record_activity(
            session, actor_id, "removed", f"{deleted.owner}/{deleted.repository}"
        )
        await session.commit()
        return True
