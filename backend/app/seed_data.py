"""Initial deadline_rules seed data.

IMPORTANT: these periods reflect commonly-cited practice under Chinese
patent examination guidelines, but statutory periods change and depend on
details (PCT national phase vs direct filing, specific notice sub-type,
etc.). Every seeded rule is marked is_verified=False on purpose — a human
must review and confirm each one in the 期限规则管理 page before the system's
calculated deadlines are relied upon for real cases.
"""
from sqlalchemy.orm import Session

from .models import DeadlineRule, DocType, PatentType

SEED_RULES: list[dict] = [
    dict(
        doc_type=DocType.OFFICE_ACTION,
        doc_variant="第一次",
        patent_type=PatentType.INVENTION,
        deadline_type="第一次审查意见通知书答复期限",
        period_value=4,
        period_unit="月",
        description="发明专利实质审查阶段第一次审查意见通知书，常见答复期限为4个月，请核对官方文书载明期限。",
    ),
    dict(
        doc_type=DocType.OFFICE_ACTION,
        doc_variant="第一次",
        patent_type=PatentType.UTILITY_MODEL,
        deadline_type="第一次审查意见通知书答复期限",
        period_value=2,
        period_unit="月",
        description="实用新型审查意见通知书，常见答复期限为2个月，请核对官方文书载明期限。",
    ),
    dict(
        doc_type=DocType.OFFICE_ACTION,
        doc_variant="第一次",
        patent_type=PatentType.DESIGN,
        deadline_type="第一次审查意见通知书答复期限",
        period_value=2,
        period_unit="月",
        description="外观设计审查意见通知书，常见答复期限为2个月，请核对官方文书载明期限。",
    ),
    dict(
        doc_type=DocType.OFFICE_ACTION,
        doc_variant="第二次",
        patent_type=None,
        deadline_type="第二次及后续审查意见通知书答复期限",
        period_value=2,
        period_unit="月",
        description="第二次及后续审查意见通知书，常见答复期限为2个月，请核对官方文书载明期限。",
    ),
    dict(
        doc_type=DocType.CORRECTION_NOTICE,
        doc_variant=None,
        patent_type=None,
        deadline_type="补正通知书答复期限",
        period_value=2,
        period_unit="月",
        description="补正通知书答复期限常见为2个月，但因主动/依职权补正、形式审查/实质审查阶段不同而可能不同，请务必核对官方文书载明期限。",
    ),
    dict(
        doc_type=DocType.REGISTRATION_NOTICE,
        doc_variant=None,
        patent_type=None,
        deadline_type="办理登记手续期限",
        period_value=2,
        period_unit="月",
        description="授权后办理登记手续（缴纳登记费/公告印刷费等）常见期限为2个月，请核对官方文书载明期限。",
    ),
    dict(
        doc_type=DocType.REEXAM_NOTICE,
        doc_variant=None,
        patent_type=None,
        deadline_type="复审通知书答复期限",
        period_value=2,
        period_unit="月",
        description="复审通知书答复期限常见为2个月，请核对官方文书载明期限。",
    ),
    dict(
        doc_type=DocType.REJECTION_DECISION,
        doc_variant=None,
        patent_type=None,
        deadline_type="提出复审请求期限",
        period_value=3,
        period_unit="月",
        description="对驳回决定不服的，可自收到驳回决定之日起3个月内请求复审（专利法第41条），请核对官方文书载明期限。",
    ),
    dict(
        doc_type=DocType.SUBSTANTIVE_EXAM_NOTICE,
        doc_variant=None,
        patent_type=None,
        deadline_type="主动修改期限",
        period_value=3,
        period_unit="月",
        description="发明专利申请人自收到进入实质审查阶段通知书之日起3个月内可主动修改申请文件。",
    ),
    dict(
        doc_type=DocType.GRANT_NOTICE,
        doc_variant=None,
        patent_type=None,
        deadline_type="办理登记手续期限",
        period_value=2,
        period_unit="月",
        description="授予专利权通知书与办理登记手续通知书同时发出，2个月内办理登记手续，逾期视为放弃取得专利权。",
    ),
    dict(
        doc_type=DocType.DEEMED_WITHDRAWN_NOTICE,
        doc_variant=None,
        patent_type=None,
        deadline_type="恢复权利请求期限",
        period_value=2,
        period_unit="月",
        description="收到视为撤回通知书后，若需请求恢复权利，常见期限为自收到通知之日起2个月，请核对官方文书载明期限。",
    ),
]


def seed_deadline_rules(db: Session) -> None:
    """Seed default rules. On an existing install only rules for document
    types that have no rule at all yet are added (types introduced by an
    update), so rules the user edited or deleted stay as they are."""
    existing_types = {row[0] for row in db.query(DeadlineRule.doc_type).distinct()}
    added = False
    for rule in SEED_RULES:
        if rule["doc_type"] in existing_types:
            continue
        db.add(DeadlineRule(**rule, is_active=True, is_verified=False))
        added = True
    if added:
        db.commit()
