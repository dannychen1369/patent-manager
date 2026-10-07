import shutil

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import CASE_FILES_DIR, get_db
from ..models import Case, CaseStage, CaseStageEvent
from ..schemas import (
    CaseCreate,
    CaseDetailOut,
    CaseOut,
    CaseStageEventOut,
    CaseUpdate,
    StageChange,
    StageEventUpdate,
)
from ..services.case_utils import generate_internal_no

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.post("", response_model=CaseOut)
def create_case(payload: CaseCreate, db: Session = Depends(get_db)):
    case = Case(
        internal_no=generate_internal_no(db),
        client_name=payload.client_name,
        patent_name=payload.patent_name,
        patent_type=payload.patent_type,
        application_no=payload.application_no,
        application_date=payload.application_date,
        agent=payload.agent,
        notes=payload.notes,
        current_stage=CaseStage.DISCLOSURE_PENDING_CONFIRM,
    )
    db.add(case)
    db.flush()
    db.add(
        CaseStageEvent(
            case_id=case.id,
            stage=CaseStage.DISCLOSURE_PENDING_CONFIRM,
            note="交底书录入，等待客户确认",
        )
    )
    db.commit()
    db.refresh(case)
    return case


@router.get("", response_model=list[CaseOut])
def list_cases(
    stage: CaseStage | None = None,
    client_name: str | None = None,
    application_no: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Case)
    if stage is not None:
        query = query.filter(Case.current_stage == stage)
    if client_name:
        query = query.filter(Case.client_name.ilike(f"%{client_name}%"))
    if application_no:
        query = query.filter(Case.application_no == application_no)
    return query.order_by(Case.created_at.desc()).all()


@router.get("/{case_id}", response_model=CaseDetailOut)
def get_case(case_id: int, db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在")
    return case


@router.patch("/{case_id}", response_model=CaseOut)
def update_case(case_id: int, payload: CaseUpdate, db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(case, field, value)
    db.commit()
    db.refresh(case)
    return case


@router.delete("/{case_id}")
def delete_case(case_id: int, db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在")
    case_dir = CASE_FILES_DIR / str(case_id)
    if case_dir.exists():
        shutil.rmtree(case_dir, ignore_errors=True)
    db.delete(case)
    db.commit()
    return {"ok": True}


@router.post("/{case_id}/confirm", response_model=CaseOut)
def confirm_case(case_id: int, db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在")
    if case.current_stage != CaseStage.DISCLOSURE_PENDING_CONFIRM:
        raise HTTPException(
            status_code=400,
            detail=f"当前阶段为「{case.current_stage}」，不是「待确认」，无法执行客户确认操作",
        )
    case.current_stage = CaseStage.PENDING_DRAFTING
    db.add(
        CaseStageEvent(
            case_id=case.id,
            stage=CaseStage.PENDING_DRAFTING,
            note="客户已确认交底书，进入待撰写阶段",
        )
    )
    db.commit()
    db.refresh(case)
    return case


@router.patch("/{case_id}/stage-events/{event_id}", response_model=CaseStageEventOut)
def update_stage_event(
    case_id: int, event_id: int, payload: StageEventUpdate, db: Session = Depends(get_db)
):
    event = db.get(CaseStageEvent, event_id)
    if not event or event.case_id != case_id:
        raise HTTPException(status_code=404, detail="阶段记录不存在")
    event.is_done = payload.is_done
    db.commit()
    db.refresh(event)
    return event


@router.post("/{case_id}/stage", response_model=CaseOut)
def change_stage(case_id: int, payload: StageChange, db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在")
    case.current_stage = payload.stage
    db.add(
        CaseStageEvent(
            case_id=case.id,
            stage=payload.stage,
            note=payload.note or "手动流转阶段",
        )
    )
    db.commit()
    db.refresh(case)
    return case
