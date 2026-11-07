import shutil

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import CASE_FILES_DIR, get_db
from ..models import Agent, Case, CaseStage, CaseStageEvent, Company
from ..schemas import (
    CaseCreate,
    CaseDetailOut,
    CaseOut,
    CaseStageEventOut,
    CaseUpdate,
    StageChange,
    StageEventUpdate,
    TwinLink,
)
from ..services.case_utils import generate_internal_no
from ..services.company_utils import get_or_create_company
from ..services.patent_type import patent_type_from_application_no
from ..services.twin import find_twin_candidates, is_valid_pair, link_twins, unlink_twin

router = APIRouter(prefix="/api/cases", tags=["cases"])


def _resolve_company(db: Session, company_id: int | None, client_name: str | None) -> Company:
    if company_id is not None:
        company = db.get(Company, company_id)
        if not company:
            raise HTTPException(status_code=404, detail="指定的企业不存在")
        return company
    company = get_or_create_company(db, client_name)
    if company is None:
        raise HTTPException(status_code=400, detail="请选择所属企业或填写客户名称")
    return company


def _resolve_agent(db: Session, agent_id: int | None) -> Agent | None:
    if agent_id is None:
        return None
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="指定的代理人不存在")
    return agent


@router.post("", response_model=CaseOut)
def create_case(payload: CaseCreate, db: Session = Depends(get_db)):
    company = _resolve_company(db, payload.company_id, payload.client_name)
    case = Case(
        internal_no=generate_internal_no(db),
        company_id=company.id,
        client_name=company.name,
        patent_name=payload.patent_name,
        # The application number's type digit is authoritative.
        patent_type=patent_type_from_application_no(payload.application_no) or payload.patent_type,
        application_no=payload.application_no,
        application_date=payload.application_date,
        agent_id=payload.agent_id,
        agent=(_resolve_agent(db, payload.agent_id).name if payload.agent_id else payload.agent),
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
    company_id: int | None = None,
    agent_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Case)
    if agent_id is not None:
        query = query.filter(Case.agent_id == agent_id)
    if company_id is not None:
        query = query.filter(Case.company_id == company_id)
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
    data = payload.model_dump(exclude_unset=True)
    if "agent_id" in data:
        agent = _resolve_agent(db, data.pop("agent_id"))
        case.agent_id = agent.id if agent else None
        case.agent = agent.name if agent else None
        data.pop("agent", None)
    company_id = data.pop("company_id", None)
    client_name = data.pop("client_name", None)
    if company_id is not None or client_name:
        # Moving the case to another company (picked, or typed by name).
        company = _resolve_company(db, company_id, client_name)
        case.company_id = company.id
        case.client_name = company.name
    for field, value in data.items():
        setattr(case, field, value)
    derived = patent_type_from_application_no(case.application_no)
    if derived is not None:
        case.patent_type = derived
    db.commit()
    db.refresh(case)
    return case


@router.delete("/{case_id}")
def delete_case(case_id: int, db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在")
    unlink_twin(db, case)
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


# ---------- 一案双申 ----------
@router.get("/{case_id}/twin-candidates", response_model=list[CaseOut])
def twin_candidates(case_id: int, db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在")
    return find_twin_candidates(db, case)


@router.post("/{case_id}/twin", response_model=CaseOut)
def set_twin(case_id: int, payload: TwinLink, db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    other = db.get(Case, payload.twin_case_id)
    if not case or not other:
        raise HTTPException(status_code=404, detail="案件不存在")
    if not is_valid_pair(case, other):
        raise HTTPException(
            status_code=400, detail="双申只能在一件发明专利和一件实用新型之间关联，请先核对两件案子的专利类型"
        )
    # Re-pairing releases whichever partners the two cases had before.
    unlink_twin(db, case)
    unlink_twin(db, other)
    link_twins(case, other)
    db.commit()
    db.refresh(case)
    return case


@router.delete("/{case_id}/twin", response_model=CaseOut)
def remove_twin(case_id: int, db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在")
    unlink_twin(db, case)
    db.commit()
    db.refresh(case)
    return case
