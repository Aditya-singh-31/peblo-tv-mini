from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class PublishResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    publish_run_id: int
    outcome: Literal["published"]
    catalogue_version: str
    catalogue_key: str
    show_count: int
    episode_count: int
