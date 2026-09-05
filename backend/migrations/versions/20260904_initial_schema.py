"""Initial schema for Peblo TV Mini.

Revision ID: 20260904_initial_schema
Revises: 
Create Date: 2026-09-04 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260904_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=120), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="editor"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=False)

    op.create_table(
        "shows",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("synopsis", sa.Text(), nullable=True),
        sa.Column("section", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("categories", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index(op.f("ix_shows_id"), "shows", ["id"], unique=False)
    op.create_index(op.f("ix_shows_title"), "shows", ["title"], unique=False)
    op.create_index(op.f("ix_shows_section"), "shows", ["section"], unique=False)
    op.create_index(op.f("ix_shows_category"), "shows", ["category"], unique=False)
    op.create_index(op.f("ix_shows_status"), "shows", ["status"], unique=False)

    op.create_table(
        "seasons",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("show_id", sa.Integer(), nullable=False),
        sa.Column("season_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["show_id"], ["shows.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("show_id", "season_number", name="uq_show_season_number"),
    )
    op.create_index(op.f("ix_seasons_id"), "seasons", ["id"], unique=False)
    op.create_index(op.f("ix_seasons_show_id"), "seasons", ["show_id"], unique=False)
    op.create_index(op.f("ix_seasons_season_number"), "seasons", ["season_number"], unique=False)
    op.create_index(op.f("ix_seasons_status"), "seasons", ["status"], unique=False)

    op.create_table(
        "episodes",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("season_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("synopsis", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("language", sa.String(length=20), nullable=True),
        sa.Column("content_group", sa.String(length=120), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["season_id"], ["seasons.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("content_group", "language", name="uq_episode_content_group_language"),
    )
    op.create_index(op.f("ix_episodes_id"), "episodes", ["id"], unique=False)
    op.create_index(op.f("ix_episodes_season_id"), "episodes", ["season_id"], unique=False)
    op.create_index(op.f("ix_episodes_title"), "episodes", ["title"], unique=False)
    op.create_index(op.f("ix_episodes_language"), "episodes", ["language"], unique=False)
    op.create_index(op.f("ix_episodes_content_group"), "episodes", ["content_group"], unique=False)
    op.create_index(op.f("ix_episodes_category"), "episodes", ["category"], unique=False)
    op.create_index(op.f("ix_episodes_status"), "episodes", ["status"], unique=False)

    op.create_table(
        "artworks",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("episode_id", sa.Integer(), nullable=True),
        sa.Column("show_id", sa.Integer(), nullable=True),
        sa.Column("artwork_type", sa.String(length=50), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["episode_id"], ["episodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["show_id"], ["shows.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_artworks_id"), "artworks", ["id"], unique=False)
    op.create_index(op.f("ix_artworks_episode_id"), "artworks", ["episode_id"], unique=False)
    op.create_index(op.f("ix_artworks_show_id"), "artworks", ["show_id"], unique=False)
    op.create_index(op.f("ix_artworks_artwork_type"), "artworks", ["artwork_type"], unique=False)
    op.create_index(op.f("ix_artworks_storage_key"), "artworks", ["storage_key"], unique=False)

    op.create_table(
        "publish_runs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("initiated_by_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="running"),
        sa.Column("outcome", sa.String(length=50), nullable=True),
        sa.Column("show_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("episode_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("catalogue_key", sa.String(length=500), nullable=True),
        sa.Column("catalogue_version", sa.String(length=120), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["initiated_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_publish_runs_id"), "publish_runs", ["id"], unique=False)
    op.create_index(op.f("ix_publish_runs_initiated_by_id"), "publish_runs", ["initiated_by_id"], unique=False)
    op.create_index(op.f("ix_publish_runs_started_at"), "publish_runs", ["started_at"], unique=False)
    op.create_index(op.f("ix_publish_runs_finished_at"), "publish_runs", ["finished_at"], unique=False)
    op.create_index(op.f("ix_publish_runs_status"), "publish_runs", ["status"], unique=False)
    op.create_index(op.f("ix_publish_runs_catalogue_key"), "publish_runs", ["catalogue_key"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_publish_runs_catalogue_key"), table_name="publish_runs")
    op.drop_index(op.f("ix_publish_runs_status"), table_name="publish_runs")
    op.drop_index(op.f("ix_publish_runs_finished_at"), table_name="publish_runs")
    op.drop_index(op.f("ix_publish_runs_started_at"), table_name="publish_runs")
    op.drop_index(op.f("ix_publish_runs_initiated_by_id"), table_name="publish_runs")
    op.drop_index(op.f("ix_publish_runs_id"), table_name="publish_runs")
    op.drop_table("publish_runs")

    op.drop_index(op.f("ix_artworks_storage_key"), table_name="artworks")
    op.drop_index(op.f("ix_artworks_artwork_type"), table_name="artworks")
    op.drop_index(op.f("ix_artworks_show_id"), table_name="artworks")
    op.drop_index(op.f("ix_artworks_episode_id"), table_name="artworks")
    op.drop_index(op.f("ix_artworks_id"), table_name="artworks")
    op.drop_table("artworks")

    op.drop_index(op.f("ix_episodes_status"), table_name="episodes")
    op.drop_index(op.f("ix_episodes_category"), table_name="episodes")
    op.drop_index(op.f("ix_episodes_content_group"), table_name="episodes")
    op.drop_index(op.f("ix_episodes_language"), table_name="episodes")
    op.drop_index(op.f("ix_episodes_title"), table_name="episodes")
    op.drop_index(op.f("ix_episodes_season_id"), table_name="episodes")
    op.drop_index(op.f("ix_episodes_id"), table_name="episodes")
    op.drop_table("episodes")

    op.drop_index(op.f("ix_seasons_status"), table_name="seasons")
    op.drop_index(op.f("ix_seasons_season_number"), table_name="seasons")
    op.drop_index(op.f("ix_seasons_show_id"), table_name="seasons")
    op.drop_index(op.f("ix_seasons_id"), table_name="seasons")
    op.drop_table("seasons")

    op.drop_index(op.f("ix_shows_status"), table_name="shows")
    op.drop_index(op.f("ix_shows_category"), table_name="shows")
    op.drop_index(op.f("ix_shows_section"), table_name="shows")
    op.drop_index(op.f("ix_shows_title"), table_name="shows")
    op.drop_index(op.f("ix_shows_id"), table_name="shows")
    op.drop_table("shows")

    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
