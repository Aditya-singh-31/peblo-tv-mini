from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.auth.security import get_db, require_role
from app.models import Episode, Season, User
from app.schemas.episode import EpisodeCreate, EpisodePage, EpisodeResponse, EpisodeUpdate
from app.validation.episode import EpisodePublicationError, validate_episode_for_publication

router = APIRouter(prefix="/admin/episodes", tags=["admin-episodes"])


def _get_episode(db: Session, episode_id: int) -> Episode:
    episode = db.execute(
        select(Episode)
        .options(selectinload(Episode.season), selectinload(Episode.artworks))
        .where(Episode.id == episode_id)
    ).scalar_one_or_none()
    if episode is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Episode not found")
    return episode


def _get_season(db: Session, season_id: int) -> Season:
    season = db.get(Season, season_id)
    if season is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Season not found")
    return season


def _to_response(episode: Episode) -> EpisodeResponse:
    return EpisodeResponse(
        id=episode.id,
        season_id=episode.season_id,
        title=episode.title,
        synopsis=episode.synopsis,
        duration_seconds=episode.duration_seconds,
        language=episode.language,
        content_group=episode.content_group,
        category=episode.category,
        status=episode.status,
        created_at=episode.created_at,
        updated_at=episode.updated_at,
        season_number=episode.season.season_number,
        artwork_count=len(episode.artworks),
    )


def _raise_validation_error(exc: EpisodePublicationError) -> None:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={"message": str(exc), "missing_fields": exc.missing_fields},
    ) from exc


def _validate_unique_content_variant(
    db: Session,
    content_group: str | None,
    language: str | None,
    episode_id: int | None = None,
) -> None:
    if content_group is None or language is None:
        return
    query = select(Episode.id).where(
        Episode.content_group == content_group,
        Episode.language == language,
    )
    if episode_id is not None:
        query = query.where(Episode.id != episode_id)
    if db.execute(query).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "An episode with this content_group and language already exists.",
                "fields": ["content_group", "language"],
            },
        )


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "An episode with this content_group and language already exists.",
                "fields": ["content_group", "language"],
            },
        ) from exc


@router.get("", response_model=EpisodePage)
def list_episodes(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, min_length=1),
    status_filter: str | None = Query(default=None, alias="status"),
    language: str | None = None,
    show_id: int | None = Query(default=None, ge=1),
    season_id: int | None = Query(default=None, ge=1),
    current_user: User = Depends(require_role("editor", "admin")),
    db: Session = Depends(get_db),
) -> EpisodePage:
    del current_user
    filters = []
    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Episode.title.ilike(term),
                Episode.synopsis.ilike(term),
                Episode.content_group.ilike(term),
            )
        )
    if status_filter:
        filters.append(Episode.status == status_filter)
    if language:
        filters.append(Episode.language == language)
    if season_id:
        filters.append(Episode.season_id == season_id)
    if show_id:
        filters.append(Season.show_id == show_id)

    base_query = select(Episode).join(Season).where(*filters)
    total = db.execute(select(func.count()).select_from(base_query.subquery())).scalar_one()
    episodes = db.execute(
        base_query
        .options(selectinload(Episode.season), selectinload(Episode.artworks))
        .order_by(Episode.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    return EpisodePage(
        items=[_to_response(episode) for episode in episodes],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{episode_id}", response_model=EpisodeResponse)
def get_episode(
    episode_id: int,
    current_user: User = Depends(require_role("editor", "admin")),
    db: Session = Depends(get_db),
) -> EpisodeResponse:
    del current_user
    return _to_response(_get_episode(db, episode_id))


@router.post("", response_model=EpisodeResponse, status_code=status.HTTP_201_CREATED)
def create_episode(
    payload: EpisodeCreate,
    current_user: User = Depends(require_role("editor", "admin")),
    db: Session = Depends(get_db),
) -> EpisodeResponse:
    del current_user
    season = _get_season(db, payload.season_id)
    values = payload.model_dump()
    _validate_unique_content_variant(db, values["content_group"], values["language"])
    if payload.status == "published":
        try:
            validate_episode_for_publication(values, artwork_count=0)
        except EpisodePublicationError as exc:
            _raise_validation_error(exc)
    episode = Episode(**values)
    db.add(episode)
    _commit(db)
    db.refresh(episode)
    episode.season = season
    episode.artworks = []
    return _to_response(episode)


@router.patch("/{episode_id}", response_model=EpisodeResponse)
def update_episode(
    episode_id: int,
    payload: EpisodeUpdate,
    current_user: User = Depends(require_role("editor", "admin")),
    db: Session = Depends(get_db),
) -> EpisodeResponse:
    del current_user
    episode = _get_episode(db, episode_id)
    updates = payload.model_dump(exclude_unset=True)
    if "season_id" in updates and updates["season_id"] is None:
        raise HTTPException(status_code=422, detail={"field": "season_id", "message": "season_id cannot be cleared"})
    if "season_id" in updates:
        season = _get_season(db, updates["season_id"])
    else:
        season = episode.season
    values = {
        "season_id": episode.season_id,
        "title": episode.title,
        "synopsis": episode.synopsis,
        "duration_seconds": episode.duration_seconds,
        "language": episode.language,
        "content_group": episode.content_group,
        "category": episode.category,
        "status": episode.status,
        **updates,
    }
    _validate_unique_content_variant(
        db,
        values["content_group"],
        values["language"],
        episode_id=episode.id,
    )
    if values["status"] == "published":
        try:
            validate_episode_for_publication(values, artwork_count=len(episode.artworks))
        except EpisodePublicationError as exc:
            _raise_validation_error(exc)
    for field_name, value in updates.items():
        setattr(episode, field_name, value)
    _commit(db)
    db.refresh(episode)
    episode.season = season
    return _to_response(episode)


@router.delete("/{episode_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
def delete_episode(
    episode_id: int,
    current_user: User = Depends(require_role("editor", "admin")),
    db: Session = Depends(get_db),
) -> None:
    del current_user
    episode = _get_episode(db, episode_id)
    db.delete(episode)
    _commit(db)
