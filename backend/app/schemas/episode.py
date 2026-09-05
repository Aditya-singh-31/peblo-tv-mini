from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


EpisodeStatus = Literal["draft", "published"]


class EpisodeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    season_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=255)
    synopsis: str | None = Field(default=None, max_length=10000)
    duration_seconds: int | None = Field(default=None, gt=0)
    language: str | None = Field(default=None, max_length=20)
    content_group: str | None = Field(default=None, max_length=120)
    category: str | None = Field(default=None, max_length=100)
    status: EpisodeStatus = "draft"

    @field_validator("title", "language", "content_group", "category")
    @classmethod
    def normalize_strings(cls, value: str | None, info):
        if value is None:
            if info.field_name == "title":
                raise ValueError("title is required")
            return None
        normalized = value.strip()
        if not normalized and info.field_name == "title":
            raise ValueError("title must not be blank")
        return normalized or None


class EpisodeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    season_id: int | None = Field(default=None, gt=0)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    synopsis: str | None = Field(default=None, max_length=10000)
    duration_seconds: int | None = Field(default=None, gt=0)
    language: str | None = Field(default=None, max_length=20)
    content_group: str | None = Field(default=None, max_length=120)
    category: str | None = Field(default=None, max_length=100)
    status: EpisodeStatus | None = None

    @field_validator("title", "language", "content_group", "category")
    @classmethod
    def normalize_strings(cls, value: str | None, info):
        if value is None and info.field_name == "title":
            raise ValueError("title cannot be cleared")
        if value is None:
            return None
        normalized = value.strip()
        if not normalized and info.field_name == "title":
            raise ValueError("title must not be blank")
        return normalized or None


class EpisodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    season_id: int
    title: str
    synopsis: str | None
    duration_seconds: int | None
    language: str | None
    content_group: str | None
    category: str | None
    status: EpisodeStatus
    created_at: datetime
    updated_at: datetime
    season_number: int
    artwork_count: int

    @computed_field
    @property
    def is_trailer(self) -> bool:
        return self.season_number == 0


class EpisodePage(BaseModel):
    items: list[EpisodeResponse]
    total: int
    page: int
    page_size: int
