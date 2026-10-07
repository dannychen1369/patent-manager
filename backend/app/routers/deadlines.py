from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Case, Deadline, DeadlineStatus
from ..schemas import DeadlineUpdate, DeadlineWithCaseOut

router = APIRouter(prefix="/api/deadlines", tags=["deadlines"])


def _to_with_case(d: Deadline) -> DeadlineWithCaseOut:
    return DeadlineWithCaseOut(
        id=d.id,
        case_id=d.case_id,
        document_id=d.document_id,
        deadline_type=d.deadline_type,
        due_date=d.due_date,
        status=d.status,
        completed_at=d.completed_at,
        note=d.note,
        created_at=d.created_at,
        case_internal_no=d.case.internal_no,
        case_client_name=d.case.client_name,
        case_patent_name=d.case.patent_name,
    )


@router.get("", response_model=list[DeadlineWithCaseOut])
def list_deadlines(
    status: DeadlineStatus | None = None,
    upcoming_days: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Deadline).join(Case)
    if status is not None:
        query = query.filter(Deadline.status == status)
    if upcoming_days is not None:
        cutoff = date.today() + timedelta(days=upcoming_days)
        query = query.filter(Deadline.due_date <= cutoff)
    deadlines = query.order_by(Deadline.due_date.asc()).all()

    today = date.today()
    changed = False
    for d in deadlines:
        if d.status == DeadlineStatus.PENDING and d.due_date < today:
            d.status = DeadlineStatus.OVERDUE
            changed = True
    if changed:
        db.commit()

    return [_to_with_case(d) for d in deadlines]


@router.patch("/{deadline_id}", response_model=DeadlineWithCaseOut)
def update_deadline(deadline_id: int, payload: DeadlineUpdate, db: Session = Depends(get_db)):
    deadline = db.get(Deadline, deadline_id)
    if not deadline:
        raise HTTPException(status_code=404, detail="期限不存在")
    data = payload.model_dump(exclude_unset=True)
    if "status" in data:
        deadline.status = data["status"]
        if data["status"] == DeadlineStatus.COMPLETED:
            deadline.completed_at = datetime.utcnow()
    if "note" in data:
        deadline.note = data["note"]
    if "due_date" in data:
        deadline.due_date = data["due_date"]
    db.commit()
    db.refresh(deadline)
    return _to_with_case(deadline)
