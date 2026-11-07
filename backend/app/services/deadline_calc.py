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
    raw_text: str | None = None,
) -> list[dict]:
    """Returns a list of {deadline_type, due_date, rule_matched, note} dicts.

    Deadlines printed in the notice itself (e.g. a fee notice's "应当于…之前
    缴纳") come first; configured rules add period-based ones on top."""
    from .doc_parser import extract_stated_deadlines

    results = [
        {
            "deadline_type": d["deadline_type"],
            "due_date": d["due_date"],
            "rule_matched": False,
            "note": "通知书中载明的截止日",
        }
        for d in (extract_stated_deadlines(raw_text) if raw_text else [])
    ]
    rules = find_matching_rules(db, doc_type, doc_variant, patent_type)
    if not rules:
        # 第三次、第四次… rarely have a rule of their own; the "第二次" rule is
        # the "第二次及后续" rule, so it covers every later round too.
        from .doc_parser import variant_ordinal

        n = variant_ordinal(doc_variant)
        if n is not None and n > 2:
            rules = find_matching_rules(db, doc_type, "第二次", patent_type)
    from .doc_parser import extract_stated_period_months

    stated_months = extract_stated_period_months(raw_text) if raw_text else None
    for rule in rules:
        value, unit = rule.period_value, rule.period_unit
        note = None
        if stated_months is not None and not (unit == "月" and value == stated_months):
            # The notice's own stated period beats the generic rule, e.g. an
            # invention's 初审-stage 审查意见通知书 is 2 months, not the
            # 4 months of a 实审 first office action.
            value, unit = stated_months, "月"
            note = f"按通知书载明的{stated_months}个月计算（规则为{rule.period_value}{rule.period_unit}）"
        elif not rule.is_verified:
            note = "该期限规则尚未人工核对，请在使用前于「期限规则管理」页面确认法定期限是否准确"
        due_date = add_period(issue_date, value, unit) if issue_date else None
        results.append(
            {
                "deadline_type": rule.deadline_type,
                "due_date": due_date,
                "rule_matched": True,
                "note": note,
            }
        )
    return results
