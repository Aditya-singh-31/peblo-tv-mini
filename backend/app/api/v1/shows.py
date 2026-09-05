from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth.security import get_db, require_role
from app.models import Episode, Season, Show, User
from app.schemas.show import ShowCreate, ShowPage, ShowResponse, ShowUpdate
from app.validation.show import ShowPublicationError, validate_show_for_publication, validate_show_reference_fields

router = APIRouter(prefix="/admin/shows", tags=["admin-shows"])


def _raise_validation_error(exc: ValueError) -> None:
    if isinstance(exc, ShowPublicationError):
        detail: str | dict[str, object] = {
            "message": str(exc),
            "missing_fields": exc.missing_fields,
        }
    else:
        detail = str(exc)
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail) from exc


def _get_show(db: Session, show_id: int) -> Show:
    show = db.get(Show, show_id)
    if show is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Show not found")
    return show


def _to_response(show: Show) -> ShowResponse:
    return ShowResponse.model_validate(show)


@router.get("", response_model=ShowPage)
def list_shows(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, min_length=1),
    section: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    language: str | None = None,
    current_user: User = Depends(require_role("editor", "admin")),
    db: Session = Depends(get_db),
) -> ShowPage:
    del current_user
    filters = []
    if search:
        term = f"%{search.strip()}%"
        filters.append(or_(Show.title.ilike(term), Show.synopsis.ilike(term)))
    if section:
        filters.append(Show.section == section)
    if status_filter:
        filters.append(Show.status == status_filter)
    if language:
        filters.append(
            Show.id.in_(
                select(Season.show_id)
                .join(Episode, Episode.season_id == Season.id)
                .where(Episode.language == language)
            )
        )

    count_query = select(func.count()).select_from(Show).where(*filters)
    total = db.execute(count_query).scalar_one()
    shows = db.execute(
        select(Show)
        .where(*filters)
        .order_by(Show.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    return ShowPage(items=shows, total=total, page=page, page_size=page_size)


@router.get("/{show_id}", response_model=ShowResponse)
def get_show(
    show_id: int,
    current_user: User = Depends(require_role("editor", "admin")),
    db: Session = Depends(get_db),
) -> ShowResponse:
    del current_user
    return _to_response(_get_show(db, show_id))


@router.post("", response_model=ShowResponse, status_code=status.HTTP_201_CREATED)
def create_show(
    payload: ShowCreate,
    current_user: User = Depends(require_role("editor", "admin")),
    db: Session = Depends(get_db),
) -> ShowResponse:
    del current_user
    values = payload.model_dump()
    try:
        validate_show_reference_fields(values)
        if payload.status == "published":
            validate_show_for_publication(values)
    except ValueError as exc:
        _raise_validation_error(exc)
    show = Show(**values)
    db.add(show)
    db.commit()
    db.refresh(show)
    return _to_response(show)


@router.patch("/{show_id}", response_model=ShowResponse)
def update_show(
    show_id: int,
    payload: ShowUpdate,
    current_user: User = Depends(require_role("editor", "admin")),
    db: Session = Depends(get_db),
) -> ShowResponse:
    del current_user
    show = _get_show(db, show_id)
    updates = payload.model_dump(exclude_unset=True)
    values = {
        "title": show.title,
        "synopsis": show.synopsis,
        "section": show.section,
        "category": show.category,
        "categories": show.categories,
        "status": show.status,
        **updates,
    }
    try:
        validate_show_reference_fields(values)
        if values["status"] == "published":
            validate_show_for_publication(values)
    except ValueError as exc:
        _raise_validation_error(exc)
    for field_name, value in updates.items():
        setattr(show, field_name, value)
    db.commit()
    db.refresh(show)
    return _to_response(show)


@router.delete("/{show_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
def delete_show(
    show_id: int,
    current_user: User = Depends(require_role("editor", "admin")),
    db: Session = Depends(get_db),
) -> None:
    del current_user
    show = _get_show(db, show_id)
    db.delete(show)
    db.commit()
