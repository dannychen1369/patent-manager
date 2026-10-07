"""Maps an incoming official document to the case stage it should advance to.

Office actions (审查意见通知书) are special-cased by their 第N次 variant so the
case lands on FIRST_EXAM / SECOND_EXAM / THIRD_EXAM_PLUS correctly.
"""
from ..models import CaseStage, DocType

_DOC_TYPE_TO_STAGE: dict[DocType, CaseStage] = {
    DocType.RECEIPT_NOTICE: CaseStage.ACCEPTED,
    DocType.PRELIM_EXAM_PASS_NOTICE: CaseStage.PRELIM_EXAM,
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

_FIRST_EXAM_VARIANTS = {"第一次"}
_SECOND_EXAM_VARIANTS = {"第二次"}


def stage_for_document(doc_type: DocType, doc_variant: str | None) -> CaseStage | None:
    if doc_type == DocType.OFFICE_ACTION:
        if doc_variant in _FIRST_EXAM_VARIANTS or doc_variant is None:
            return CaseStage.FIRST_EXAM
        if doc_variant in _SECOND_EXAM_VARIANTS:
            return CaseStage.SECOND_EXAM
        return CaseStage.THIRD_EXAM_PLUS
    return _DOC_TYPE_TO_STAGE.get(doc_type)
