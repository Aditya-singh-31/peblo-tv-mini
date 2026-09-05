from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


ValidationSeverity = Literal["error", "warning"]
ValidationEntityType = Literal["show", "season", "episode", "artwork", "other"]


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: ValidationSeverity
    entity_type: ValidationEntityType
    entity_id: int | None
    show_title: str | None
    season_title: str | None
    episode_title: str | None
    field: str
    problem: str
    suggested_fix: str


class ValidationReport(BaseModel):
    can_publish: bool
    total_issues: int
    issues: list[ValidationIssue]
    groups: dict[str, list[ValidationIssue]]
