from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PublishRun(Base):
    __tablename__ = "publish_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    initiated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    started_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="running", index=True)
    outcome: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    show_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    episode_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    catalogue_key: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    catalogue_version: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
