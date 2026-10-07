import calendar
from datetime import date

from sqlalchemy.orm import Session

from ..models import DeadlineRule, DocType, PatentType


def add_period(base: date, value: int, unit: str) -> date:
    """Add `value` days or months to `base`. Calendar-day math only —
    does NOT account for statutory holiday extensions. Verify against
    the official calendar before treating the result as final for a
    real deadline.
    """
    if unit == "天":
        from datetime import timedelta

        return base + timedelta(days=value)
    if unit == "月":
        month_index = base.month - 1 + value
        year = base.year + month_index // 12
        month = month_index % 12 + 1
        day = min(base.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)
    raise ValueError(f"未知的期限单位: {unit}")


def find_matching_rules(
    db: Session,
    doc_type: DocType,
    doc_variant: str | None,
    patent_type: PatentType | None,
) -> list[DeadlineRule]:
    """Picks the most specific active rules for this doc_type.

    A rule with doc_variant/patent_type set to None acts as a generic
    fallback. Among matching rules we prefer variant-specific ones over
    generic ones, and (within that) patent-type-specific ones over generic.
    """
    candidates = db.query(DeadlineRule).filter(
        DeadlineRule.doc_type == doc_type, DeadlineRule.is_active.is_(True)
    ).all()

    def variant_ok(r: DeadlineRule) -> bool:
        return r.doc_variant is None or r.doc_variant == doc_variant

    def patent_ok(r: DeadlineRule) -> bool:
        return r.patent_type is None or r.patent_type == patent_type

    candidates = [r for r in candidates if variant_ok(r) and patent_ok(r)]
    if not candidates:
        return []

    has_specific_variant = any(r.doc_variant is not None for r in candidates)
    if has_specific_variant:
        candidates = [r for r in candidates if r.doc_variant is not None]

    has_specific_patent_type = any(r.patent_type is not None for r in candidates)
    if has_specific_patent_type:
        candidates = [r for r in candidates if r.patent_type is not None]

    return candidates


def calculate_deadlines(
    db: Session,
    doc_type: DocType,
    doc_variant: str | None,
    patent_type: PatentType | None,
    issue_date: date | None,
) -> list[dict]:
    """Returns a list of {deadline_type, due_date, rule_matched, note} dicts."""
    rules = find_matching_rules(db, doc_type, doc_variant, patent_type)
    if not rules:
        return []
    results = []
    for rule in rules:
        due_date = add_period(issue_date, rule.period_value, rule.period_unit) if issue_date else None
        note = None
        if not rule.is_verified:
            note = "该期限规则尚未人工核对，请在使用前于「期限规则管理」页面确认法定期限是否准确"
        results.append(
            {
                "deadline_type": rule.deadline_type,
                "due_date": due_date,
                "rule_matched": True,
                "note": note,
            }
        )
    return results
