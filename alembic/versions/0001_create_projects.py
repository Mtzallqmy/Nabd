"""Create projects table.

Revision ID: 0001_create_projects
Revises:
"""

import sqlalchemy as sa

from alembic import op

revision = "0001_create_projects"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("repository", sa.String(length=255), nullable=False),
        sa.Column("registered_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_projects_owner", "projects", ["owner"])
    op.create_index("ix_projects_repository", "projects", ["repository"])


def downgrade():
    op.drop_index("ix_projects_repository", table_name="projects")
    op.drop_index("ix_projects_owner", table_name="projects")
    op.drop_table("projects")
