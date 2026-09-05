from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class PublishRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    initiated_by_id: int | None
    started_at: datetime
    finished_at: datetime | None
    status: str
    outcome: str | None
    show_count: int
    episode_count: int
    catalogue_key: str | None
    catalogue_version: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class PublishHistoryPage(BaseModel):
    items: list[PublishRunResponse]
    total: int
    page: int
    page_size: int
