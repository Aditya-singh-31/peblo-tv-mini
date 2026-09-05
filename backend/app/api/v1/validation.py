from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.security import get_db, require_role
from app.models import User
from app.schemas.validation_report import ValidationReport
from app.validation.report import build_validation_report

router = APIRouter(prefix="/admin", tags=["admin-validation"])


@router.get("/validation-report", response_model=ValidationReport)
def validation_report(
    current_user: User = Depends(require_role("editor", "admin")),
    db: Session = Depends(get_db),
) -> ValidationReport:
    del current_user
    return build_validation_report(db)
