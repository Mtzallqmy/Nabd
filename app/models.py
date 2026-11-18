from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def now_utc() -> datetime:
    return datetime.now(UTC)


class UserModel(Base):
    __tablename__ = "telegram_users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class ProjectModel(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner: Mapped[str] = mapped_column(String(255), index=True)
    repository: Mapped[str] = mapped_column(String(255), index=True)
    registered_by: Mapped[int] = mapped_column(
        ForeignKey("telegram_users.id", name="fk_projects_registered_by")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(), default=lambda: now_utc().replace(tzinfo=None)
    )

    __table_args__ = (
        Index("uq_projects_slug_ci", func.lower(owner), func.lower(repository), unique=True),
        {"sqlite_autoincrement": True},
    )

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.repository}"


class ActivityModel(Base):
    __tablename__ = "project_activity"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("telegram_users.id"), index=True)
    action: Mapped[str] = mapped_column(String(32))
    project: Mapped[str] = mapped_column(String(511))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
