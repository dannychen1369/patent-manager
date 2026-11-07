"""Maps an incoming official document to the case stage it should advance to.

Office actions (审查意见通知书) are special-cased by their 第N次 variant so the
case lands on FIRST_EXAM / SECOND_EXAM / THIRD_EXAM_PLUS correctly.
"""
from ..models import CaseStage, DocType
from .doc_parser import variant_ordinal

_DOC_TYPE_TO_STAGE: dict[DocType, CaseStage] = {
    DocType.RECEIPT_NOTICE: CaseStage.ACCEPTED,
    DocType.PRELIM_EXAM_PASS_NOTICE: CaseStage.PRELIM_EXAM,
    DocType.PUBLICATION_NOTICE: CaseStage.PUBLISHED,
    DocType.SUBSTANTIVE_EXAM_NOTICE: CaseStage.SUBSTANTIVE_EXAM,
    DocType.CORRECTION_NOTICE: CaseStage.CORRECTION,
    DocType.DEEMED_WITHDRAWN_NOTICE: CaseStage.DEEMED_WITHDRAWN,
    DocType.REJECTION_DECISION: CaseStage.REJECTED,
    DocType.REEXAM_ACCEPTANCE_NOTICE: CaseStage.REEXAMINATION,
    DocType.REEXAM_NOTICE: CaseStage.REEXAMINATION,
    DocType.INVALIDATION_NOTICE: CaseStage.INVALIDATION,
    DocType.INVALIDATION_DECISION: CaseStage.INVALIDATION,
    DocType.GRANT_NOTICE: CaseStage.GRANTED,
    DocType.REGISTRATION_NOTICE: CaseStage.REGISTRATION,
}


def stage_for_document(doc_type: DocType, doc_variant: str | None) -> CaseStage | None:
    if doc_type == DocType.OFFICE_ACTION:
        n = variant_ordinal(doc_variant)
        if n is None or n <= 1:
            return CaseStage.FIRST_EXAM
        if n == 2:
            return CaseStage.SECOND_EXAM
        return CaseStage.THIRD_EXAM_PLUS
    return _DOC_TYPE_TO_STAGE.get(doc_type)


# Normal forward order of prosecution stages, used to break ties between
# notices issued on the same day (公布通知书 and 进入实质审查阶段通知书 often
# share a date): the case lands on the further-along one.
STAGE_ORDER: list[CaseStage] = [
    CaseStage.FILED,
    CaseStage.ACCEPTED,
    CaseStage.PRELIM_EXAM,
    CaseStage.PUBLISHED,
    CaseStage.SUBSTANTIVE_EXAM,
    CaseStage.FIRST_EXAM,
    CaseStage.SECOND_EXAM,
    CaseStage.THIRD_EXAM_PLUS,
    CaseStage.GRANTED,
    CaseStage.REGISTRATION,
]


def stage_rank(stage: CaseStage | None) -> int:
    try:
        return STAGE_ORDER.index(stage)
    except ValueError:
        return -1
