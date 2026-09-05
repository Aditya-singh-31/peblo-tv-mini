from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import get_db, require_role
from app.models import Season, Show, User
from app.schemas.season import SeasonCreate, SeasonResponse, SeasonUpdate

router = APIRouter(prefix="/admin", tags=["admin-seasons"])


def _get_show(db: Session, show_id: int) -> Show:
    show = db.get(Show, show_id)
    if show is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Show not found")
    return show


def _get_season(db: Session, season_id: int) -> Season:
    season = db.get(Season, season_id)
    if season is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Season not found")
    return season


def _to_response(season: Season) -> SeasonResponse:
    return SeasonResponse.model_validate(season)


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A season with this number already exists for the show",
        ) from exc


@router.get("/shows/{show_id}/seasons", response_model=list[SeasonResponse])
def list_seasons(
    show_id: int,
    current_user: User = Depends(require_role("editor", "admin")),
    db: Session = Depends(get_db),
) -> list[SeasonResponse]:
    del current_user
    _get_show(db, show_id)
    seasons = db.execute(
        select(Season)
        .where(Season.show_id == show_id)
        .order_by(Season.season_number, Season.id)
    ).scalars().all()
    return [_to_response(season) for season in seasons]


@router.post(
    "/shows/{show_id}/seasons",
    response_model=SeasonResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_season(
    show_id: int,
    payload: SeasonCreate,
    current_user: User = Depends(require_role("editor", "admin")),
    db: Session = Depends(get_db),
) -> SeasonResponse:
    del current_user
    _get_show(db, show_id)
    season = Season(show_id=show_id, **payload.model_dump())
    db.add(season)
    _commit(db)
    db.refresh(season)
    return _to_response(season)


@router.get("/seasons/{season_id}", response_model=SeasonResponse)
def get_season(
    season_id: int,
    current_user: User = Depends(require_role("editor", "admin")),
    db: Session = Depends(get_db),
) -> SeasonResponse:
    del current_user
    return _to_response(_get_season(db, season_id))


@router.patch("/seasons/{season_id}", response_model=SeasonResponse)
def update_season(
    season_id: int,
    payload: SeasonUpdate,
    current_user: User = Depends(require_role("editor", "admin")),
    db: Session = Depends(get_db),
) -> SeasonResponse:
    del current_user
    season = _get_season(db, season_id)
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(season, field_name, value)
    _commit(db)
    db.refresh(season)
    return _to_response(season)


@router.delete("/seasons/{season_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
def delete_season(
    season_id: int,
    current_user: User = Depends(require_role("editor", "admin")),
    db: Session = Depends(get_db),
) -> None:
    del current_user
    season = _get_season(db, season_id)
    db.delete(season)
    _commit(db)
