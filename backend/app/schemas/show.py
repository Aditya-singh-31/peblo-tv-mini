from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ShowStatus = Literal["draft", "published"]


class ShowFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    synopsis: str | None = Field(default=None, max_length=10000)
    section: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=100)
    categories: str | None = Field(default=None, max_length=500)
    status: ShowStatus = "draft"

    @field_validator("title", "synopsis", "section", "category", "categories")
    @classmethod
    def blank_strings_are_null_or_invalid(cls, value: str | None, info):
        if value is not None and not value.strip():
            if info.field_name == "title":
                raise ValueError("title must not be blank")
            return None
        return value


class ShowCreate(ShowFields):
    pass


class ShowUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=255)
    synopsis: str | None = Field(default=None, max_length=10000)
    section: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=100)
    categories: str | None = Field(default=None, max_length=500)
    status: ShowStatus | None = None

    @field_validator("title", "synopsis", "section", "category", "categories")
    @classmethod
    def blank_strings_are_null_or_invalid(cls, value: str | None, info):
        if value is not None and not value.strip():
            if info.field_name == "title":
                raise ValueError("title must not be blank")
            return None
        return value


class ShowResponse(ShowFields):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class ShowPage(BaseModel):
    items: list[ShowResponse]
    total: int
    page: int
    page_size: int
