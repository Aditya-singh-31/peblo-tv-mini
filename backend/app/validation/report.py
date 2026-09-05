from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Artwork, Episode, Season, Show
from app.schemas.validation_report import ValidationIssue, ValidationReport
from app.validation.artwork import ARTWORK_SPECS

_REFERENCE_PATH = Path(__file__).resolve().parents[4] / "challenge" / "reference.json"


def _reference_data() -> dict[str, Any]:
    try:
        data = json.loads(_REFERENCE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _allowed_values(reference: dict[str, Any], *names: str) -> set[str]:
    values: Any = None
    for name in names:
        candidate = reference.get(name)
        if isinstance(candidate, list):
            values = candidate
            break
        if isinstance(candidate, dict):
            for nested_name in ("allowed", "values", "options"):
                nested = candidate.get(nested_name)
                if isinstance(nested, list):
                    values = nested
                    break
        if values is not None:
            break
    return {str(value) for value in values or []}


def _issue(
    *,
    entity_type: str,
    entity_id: int | None,
    show_title: str | None,
    season_title: str | None,
    episode_title: str | None,
    field: str,
    problem: str,
    suggested_fix: str,
)-> ValidationIssue:
    return ValidationIssue(
        severity="error",
        entity_type=entity_type,  # type: ignore[arg-type]
        entity_id=entity_id,
        show_title=show_title,
        season_title=season_title,
        episode_title=episode_title,
        field=field,
        problem=problem,
        suggested_fix=suggested_fix,
    )


def _reference_issue(
    *,
    entity_type: str,
    entity_id: int,
    show_title: str | None,
    season_title: str | None,
    episode_title: str | None,
    field: str,
    value: Any,
    allowed: set[str],
) -> ValidationIssue:
    label = entity_type.title()
    return _issue(
        entity_type=entity_type,
        entity_id=entity_id,
        show_title=show_title,
        season_title=season_title,
        episode_title=episode_title,
        field=field,
        problem=f"{label} has unsupported {field} value '{value}'.",
        suggested_fix=f"Set {field} to one of: {', '.join(sorted(allowed))}.",
    )


def _add_show_issues(show: Show, reference: dict[str, Any], issues: list[ValidationIssue]) -> None:
    if show.status == "published" and not (show.section or "").strip():
        issues.append(
            _issue(
                entity_type="show",
                entity_id=show.id,
                show_title=show.title,
                season_title=None,
                episode_title=None,
                field="section",
                problem=f"Show '{show.title}' cannot be published because no section has been selected.",
                suggested_fix="Select a valid section for the show.",
            )
        )
    for field, value, names in (
        ("section", show.section, ("sections", "section")),
        ("category", show.category, ("categories", "category")),
        ("status", show.status, ("statuses", "show_statuses", "show_status")),
    ):
        allowed = _allowed_values(reference, *names)
        if show.status == "published" and allowed and value is not None and value not in allowed:
            issues.append(
                _reference_issue(
                    entity_type="show",
                    entity_id=show.id,
                    show_title=show.title,
                    season_title=None,
                    episode_title=None,
                    field=field,
                    value=value,
                    allowed=allowed,
                )
            )


def _add_season_issues(season: Season, show: Show | None, reference: dict[str, Any], issues: list[ValidationIssue]) -> None:
    show_title = show.title if show else None
    if show is None and season.status == "published":
        issues.append(
            _issue(
                entity_type="season",
                entity_id=season.id,
                show_title=None,
                season_title=season.title,
                episode_title=None,
                field="show_id",
                problem=f"Season '{season.title or season.season_number}' is not linked to an existing show.",
                suggested_fix="Assign the season to an existing show.",
            )
        )
    if season.status == "published" and season.season_number < 0:
        issues.append(
            _issue(
                entity_type="season",
                entity_id=season.id,
                show_title=show_title,
                season_title=season.title,
                episode_title=None,
                field="season_number",
                problem="Season number cannot be negative.",
                suggested_fix="Use 0 for trailers or a positive number for an ordinary season.",
            )
        )
    allowed = _allowed_values(reference, "statuses", "season_statuses", "season_status")
    if allowed and season.status not in allowed:
        issues.append(
            _reference_issue(
                entity_type="season",
                entity_id=season.id,
                show_title=show_title,
                season_title=season.title,
                episode_title=None,
                field="status",
                value=season.status,
                allowed=allowed,
            )
        )


def _add_episode_issues(
    episode: Episode,
    season: Season | None,
    show: Show | None,
    reference: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    show_title = show.title if show else None
    season_title = season.title if season else None
    if season is None and episode.status == "published":
        issues.append(
            _issue(
                entity_type="episode",
                entity_id=episode.id,
                show_title=show_title,
                season_title=None,
                episode_title=episode.title,
                field="season_id",
                problem=f"Episode '{episode.title}' is not linked to an existing season.",
                suggested_fix="Assign the episode to an existing season.",
            )
        )
    if episode.status == "published" and (episode.duration_seconds is None or episode.duration_seconds <= 0):
        issues.append(
            _issue(
                entity_type="episode",
                entity_id=episode.id,
                show_title=show_title,
                season_title=season_title,
                episode_title=episode.title,
                field="duration_seconds",
                problem=f"Episode '{episode.title}' cannot be published because its duration is missing.",
                suggested_fix="Enter the episode duration in seconds.",
            )
        )
    if episode.status == "published" and not episode.artworks:
        issues.append(
            _issue(
                entity_type="episode",
                entity_id=episode.id,
                show_title=show_title,
                season_title=season_title,
                episode_title=episode.title,
                field="artwork",
                problem=f"Episode '{episode.title}' cannot be published because required artwork is missing.",
                suggested_fix="Attach at least one valid artwork asset to the episode.",
            )
        )
    for field, value, names in (
        ("language", episode.language, ("languages", "language")),
        ("category", episode.category, ("categories", "category")),
        ("status", episode.status, ("statuses", "episode_statuses", "episode_status")),
    ):
        allowed = _allowed_values(reference, *names)
        if episode.status == "published" and allowed and value is not None and value not in allowed:
            issues.append(
                _reference_issue(
                    entity_type="episode",
                    entity_id=episode.id,
                    show_title=show_title,
                    season_title=season_title,
                    episode_title=episode.title,
                    field=field,
                    value=value,
                    allowed=allowed,
                )
            )


def _add_artwork_issues(artwork: Artwork, episode: Episode | None, show: Show | None, issues: list[ValidationIssue]) -> None:
    if show is None and episode is not None and episode.season is not None:
        show = episode.season.show
    show_title = show.title if show else None
    season_title = episode.season.title if episode and episode.season else None
    episode_title = episode.title if episode else None
    kind = artwork.artwork_type.upper()
    spec = ARTWORK_SPECS.get(kind)
    if spec is None:
        issues.append(
            _issue(
                entity_type="artwork",
                entity_id=artwork.id,
                show_title=show_title,
                season_title=season_title,
                episode_title=episode_title,
                field="artwork_type",
                problem=f"Artwork '{artwork.artwork_type}' is not a supported artwork type.",
                suggested_fix="Use POSTER, BANNER, or THUMBNAIL.",
            )
        )
        return
    if artwork.width is None or artwork.height is None:
        return
    actual_ratio = artwork.width / artwork.height if artwork.height else 0
    expected_ratio = spec.ratio_width / spec.ratio_height
    if abs(actual_ratio - expected_ratio) > 0.02:
        label = artwork.artwork_type.title()
        issues.append(
            _issue(
                entity_type="artwork",
                entity_id=artwork.id,
                show_title=show_title,
                season_title=season_title,
                episode_title=episode_title,
                field="aspect_ratio",
                problem=f"{label} has an invalid aspect ratio.",
                suggested_fix=f"Upload artwork with a {spec.ratio_width}:{spec.ratio_height} aspect ratio.",
            )
        )


def _add_duplicate_issues(episodes: Iterable[Episode], issues: list[ValidationIssue]) -> None:
    variants: dict[tuple[str, str], list[Episode]] = {}
    for episode in episodes:
        if episode.content_group is None or episode.language is None:
            continue
        variants.setdefault((episode.content_group, episode.language), []).append(episode)
    for (content_group, language), duplicates in variants.items():
        if len(duplicates) < 2:
            continue
        for episode in duplicates:
            show = episode.season.show if episode.season else None
            season = episode.season
            issues.append(
                _issue(
                    entity_type="episode",
                    entity_id=episode.id,
                    show_title=show.title if show else None,
                    season_title=season.title if season else None,
                    episode_title=episode.title,
                    field="content_group",
                    problem=f"Episode '{episode.title}' duplicates content group '{content_group}' for language '{language}'.",
                    suggested_fix="Use a unique content_group for this language or choose a different language.",
                )
            )


def build_validation_report(db: Session) -> ValidationReport:
    reference = _reference_data()
    shows = db.execute(select(Show).order_by(Show.id)).scalars().all()
    seasons = db.execute(
        select(Season).options(selectinload(Season.show)).order_by(Season.id)
    ).scalars().all()
    episodes = db.execute(
        select(Episode)
        .options(selectinload(Episode.season).selectinload(Season.show), selectinload(Episode.artworks))
        .order_by(Episode.id)
    ).scalars().all()
    artworks = db.execute(
        select(Artwork)
        .options(selectinload(Artwork.episode).selectinload(Episode.season).selectinload(Season.show))
        .order_by(Artwork.id)
    ).scalars().all()

    issues: list[ValidationIssue] = []
    for show in shows:
        _add_show_issues(show, reference, issues)
    for season in seasons:
        _add_season_issues(season, season.show, reference, issues)
    for episode in episodes:
        _add_episode_issues(episode, episode.season, episode.season.show if episode.season else None, reference, issues)
    for artwork in artworks:
        _add_artwork_issues(artwork, artwork.episode, None, issues)
    _add_duplicate_issues(episodes, issues)

    groups = {key: [] for key in ("show", "season", "episode", "artwork", "other")}
    for item in issues:
        groups[item.entity_type].append(item)
    return ValidationReport(
        can_publish=not issues,
        total_issues=len(issues),
        issues=issues,
        groups=groups,
    )


def ensure_publishable(db: Session) -> ValidationReport:
    report = build_validation_report(db)
    if not report.can_publish:
        raise ValueError(report.model_dump())
    return report
