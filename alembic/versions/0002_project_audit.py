"""Preserve existing projects and add user records and activity."""

import sqlalchemy as sa

from alembic import op

revision = "0002_project_audit"
down_revision = "0001_create_projects"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "telegram_users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        "INSERT INTO telegram_users (id, created_at) "
        "SELECT DISTINCT registered_by, CURRENT_TIMESTAMP FROM projects"
    )
    with op.batch_alter_table("projects", table_kwargs={"sqlite_autoincrement": True}) as batch:
        batch.alter_column(
            "registered_by",
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=False,
        )
        batch.create_foreign_key(
            "fk_projects_registered_by",
            "telegram_users",
            ["registered_by"],
            ["id"],
        )
    op.create_index(
        "uq_projects_slug_ci",
        "projects",
        [sa.text("lower(owner)"), sa.text("lower(repository)")],
        unique=True,
    )
    op.create_table(
        "project_activity",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.BigInteger(), sa.ForeignKey("telegram_users.id"), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("project", sa.String(511), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_project_activity_actor_id", "project_activity", ["actor_id"])


def downgrade():
    op.drop_table("project_activity")
    op.drop_index("uq_projects_slug_ci", table_name="projects")
    with op.batch_alter_table("projects") as batch:
        batch.drop_constraint("fk_projects_registered_by", type_="foreignkey")
        batch.alter_column(
            "registered_by",
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=False,
        )
    op.drop_table("telegram_users")
