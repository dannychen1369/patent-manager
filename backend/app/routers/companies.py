from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Case, Company, Deadline, DeadlineStatus
from ..schemas import CompanyCreate, CompanyDetailOut, CompanyOut, CompanyUpdate
from ..services.company_utils import normalize_company_name

router = APIRouter(prefix="/api/companies", tags=["companies"])


def _get_company_or_404(db: Session, company_id: int) -> Company:
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="企业不存在")
    return company


def _counts(db: Session, company_ids: list[int]) -> tuple[dict[int, int], dict[int, int]]:
    if not company_ids:
        return {}, {}
    case_counts = dict(
        db.query(Case.company_id, func.count(Case.id))
        .filter(Case.company_id.in_(company_ids))
        .group_by(Case.company_id)
        .all()
    )
    deadline_counts = dict(
        db.query(Case.company_id, func.count(Deadline.id))
        .join(Deadline, Deadline.case_id == Case.id)
        .filter(Case.company_id.in_(company_ids), Deadline.status == DeadlineStatus.PENDING)
        .group_by(Case.company_id)
        .all()
    )
    return case_counts, deadline_counts


def _to_out(company: Company, case_counts: dict, deadline_counts: dict) -> CompanyOut:
    out = CompanyOut.model_validate(company)
    out.case_count = case_counts.get(company.id, 0)
    out.pending_deadline_count = deadline_counts.get(company.id, 0)
    return out


def _require_unique_name(db: Session, name: str, exclude_id: int | None = None) -> str:
    normalized = normalize_company_name(name)
    if not normalized:
        raise HTTPException(status_code=400, detail="企业名称不能为空")
    query = db.query(Company).filter(Company.name == normalized)
    if exclude_id is not None:
        query = query.filter(Company.id != exclude_id)
    if query.first():
        raise HTTPException(status_code=400, detail=f"企业「{normalized}」已存在")
    return normalized


@router.get("", response_model=list[CompanyOut])
def list_companies(keyword: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Company)
    if keyword:
        query = query.filter(Company.name.ilike(f"%{keyword}%"))
    companies = query.order_by(Company.created_at.desc()).all()
    case_counts, deadline_counts = _counts(db, [c.id for c in companies])
    return [_to_out(c, case_counts, deadline_counts) for c in companies]


@router.post("", response_model=CompanyOut)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["name"] = _require_unique_name(db, payload.name)
    company = Company(**data)
    db.add(company)
    db.commit()
    db.refresh(company)
    return _to_out(company, {}, {})


@router.get("/{company_id}", response_model=CompanyDetailOut)
def get_company(company_id: int, db: Session = Depends(get_db)):
    company = _get_company_or_404(db, company_id)
    case_counts, deadline_counts = _counts(db, [company.id])
    out = CompanyDetailOut.model_validate(company)
    out.case_count = case_counts.get(company.id, 0)
    out.pending_deadline_count = deadline_counts.get(company.id, 0)
    return out


@router.patch("/{company_id}", response_model=CompanyOut)
def update_company(company_id: int, payload: CompanyUpdate, db: Session = Depends(get_db)):
    company = _get_company_or_404(db, company_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        data["name"] = _require_unique_name(db, data["name"] or "", exclude_id=company.id)
    for field, value in data.items():
        setattr(company, field, value)
    if "name" in data:
        # Keep the mirrored client_name on every case in sync with the rename.
        for case in company.cases:
            case.client_name = company.name
    db.commit()
    db.refresh(company)
    case_counts, deadline_counts = _counts(db, [company.id])
    return _to_out(company, case_counts, deadline_counts)


@router.delete("/{company_id}")
def delete_company(company_id: int, db: Session = Depends(get_db)):
    company = _get_company_or_404(db, company_id)
    case_count = db.query(func.count(Case.id)).filter(Case.company_id == company.id).scalar()
    if case_count:
        raise HTTPException(
            status_code=400,
            detail=f"该企业下还有 {case_count} 个案件，请先删除这些案件或把它们转到其他企业",
        )
    db.delete(company)
    db.commit()
    return {"ok": True}
