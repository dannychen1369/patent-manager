"""一案双申: the same applicant files an invention and a utility model for the
same creation on the same day (专利法第9条第1款). Application numbers are
independent serials, so the pair can't be found from the numbers; it's
identified by same applicant + same application date + one 发明 and one
实用新型 + the same title.
"""
import re

from sqlalchemy.orm import Session

from ..models import Case, PatentType

_PAIR = {PatentType.INVENTION: PatentType.UTILITY_MODEL, PatentType.UTILITY_MODEL: PatentType.INVENTION}
_NAME_NOISE = re.compile(r"[\s，,。.、；;：:（）()\[\]【】\"'“”‘’]")


def _normalize_name(name: str | None) -> str:
    return _NAME_NOISE.sub("", name or "")


def is_valid_pair(a: Case, b: Case) -> bool:
    return a.id != b.id and _PAIR.get(a.patent_type) == b.patent_type


def find_twin_candidates(db: Session, case: Case, same_name_only: bool = False) -> list[Case]:
    """Cases that could be this case's 双申 counterpart: same applicant, same
    application date, the complementary patent type, and not already paired
    with some other case."""
    other_type = _PAIR.get(case.patent_type)
    if other_type is None or case.application_date is None:
        return []
    query = db.query(Case).filter(
        Case.id != case.id,
        Case.patent_type == other_type,
        Case.application_date == case.application_date,
    )
    if case.company_id is not None:
        query = query.filter(Case.company_id == case.company_id)
    else:
        query = query.filter(Case.client_name == case.client_name)
    candidates = [c for c in query.all() if c.twin_case_id in (None, case.id)]
    if same_name_only:
        own = _normalize_name(case.patent_name)
        candidates = [c for c in candidates if own and _normalize_name(c.patent_name) == own]
    return candidates


def link_twins(a: Case, b: Case) -> None:
    a.twin_case_id = b.id
    b.twin_case_id = a.id


def unlink_twin(db: Session, case: Case) -> None:
    if case.twin_case_id is not None:
        other = db.get(Case, case.twin_case_id)
        if other is not None and other.twin_case_id == case.id:
            other.twin_case_id = None
    case.twin_case_id = None


def auto_link_twin(db: Session, case: Case) -> bool:
    """Pair automatically only when it's unambiguous: exactly one candidate
    with the same title. Anything looser is left for the user to confirm
    from the candidate list on the case page."""
    if case.twin_case_id is not None:
        return False
    matches = find_twin_candidates(db, case, same_name_only=True)
    if len(matches) != 1:
        return False
    link_twins(case, matches[0])
    return True


def backfill_twins(db: Session) -> None:
    changed = False
    for case in db.query(Case).filter(
        Case.twin_case_id.is_(None), Case.patent_type == PatentType.INVENTION
    ).all():
        changed = auto_link_twin(db, case) or changed
    if changed:
        db.commit()
