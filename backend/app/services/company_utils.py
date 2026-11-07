from sqlalchemy.orm import Session

from ..models import Agent, Case, Company, Document
from .patent_type import patent_type_from_application_no

# Placeholder client names that must never turn into a real company record.
_PLACEHOLDER_NAMES = {"", "待补充", "未知"}


def normalize_company_name(name: str | None) -> str | None:
    if name is None:
        return None
    cleaned = name.strip().strip("，,；;")
    # Full-width/half-width parentheses are used interchangeably in Chinese
    # company names; normalize so "某某（北京）有限公司" and "某某(北京)有限公司"
    # don't end up as two different companies.
    cleaned = cleaned.replace("(", "（").replace(")", "）")
    if cleaned in _PLACEHOLDER_NAMES:
        return None
    return cleaned


def find_company_by_name(db: Session, name: str | None) -> Company | None:
    normalized = normalize_company_name(name)
    if not normalized:
        return None
    return db.query(Company).filter(Company.name == normalized).first()


def get_or_create_company(db: Session, name: str | None) -> Company | None:
    normalized = normalize_company_name(name)
    if not normalized:
        return None
    company = db.query(Company).filter(Company.name == normalized).first()
    if company is None:
        company = Company(name=normalized)
        db.add(company)
        db.flush()
    return company


def backfill_case_companies(db: Session) -> None:
    """One-time-ish (idempotent) upgrade step: cases created before companies
    existed only have a free-text client_name. Group them under a company of
    the same name so the company view shows them."""
    orphans = db.query(Case).filter(Case.company_id.is_(None)).all()
    changed = False
    for case in orphans:
        company = get_or_create_company(db, case.client_name)
        if company is not None:
            case.company_id = company.id
            changed = True
    if changed:
        db.commit()


def backfill_case_patent_types(db: Session) -> None:
    """Make every case's patent type agree with its application number.

    Covers both cases saved as 未知 and cases mis-typed by the old keyword
    guess (a 实用新型 notice mentioning "发明" got saved as 发明专利)."""
    with_no = db.query(Case).filter(Case.application_no.is_not(None)).all()
    changed = False
    for case in with_no:
        derived = patent_type_from_application_no(case.application_no)
        if derived is not None and case.patent_type != derived:
            case.patent_type = derived
            changed = True
    for doc in db.query(Document).filter(Document.application_no.is_not(None)).all():
        derived = patent_type_from_application_no(doc.application_no)
        if derived is not None and doc.patent_type != derived:
            doc.patent_type = derived
            changed = True
    if changed:
        db.commit()


def backfill_case_agents(db: Session) -> None:
    """Cases from before the roster have a typed 承办人 name only. Put each
    distinct name on the roster (unless someone by that name already is) and
    link the cases to it."""
    pending = (
        db.query(Case)
        .filter(Case.agent_id.is_(None), Case.agent.is_not(None), Case.agent != "")
        .all()
    )
    changed = False
    for case in pending:
        name = case.agent.strip()
        if not name:
            continue
        same_name = db.query(Agent).filter(Agent.name == name).all()
        if len(same_name) > 1:
            continue  # ambiguous 同名: leave it for the user to pick
        agent = same_name[0] if same_name else Agent(name=name)
        if not same_name:
            db.add(agent)
            db.flush()
        case.agent_id = agent.id
        changed = True
    if changed:
        db.commit()
