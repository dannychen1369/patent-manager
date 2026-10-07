from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from .models import CaseStage, DeadlineStatus, DocType, PatentType


# ---------- Case ----------
class CaseCreate(BaseModel):
    client_name: str
    patent_name: str
    patent_type: PatentType = PatentType.UNKNOWN
    application_no: str | None = None
    application_date: date | None = None
    agent: str | None = None
    notes: str | None = None


class CaseUpdate(BaseModel):
    client_name: str | None = None
    patent_name: str | None = None
    patent_type: PatentType | None = None
    application_no: str | None = None
    application_date: date | None = None
    agent: str | None = None
    notes: str | None = None


class StageChange(BaseModel):
    stage: CaseStage
    note: str | None = None


class CaseStageEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stage: CaseStage
    changed_at: datetime
    note: str | None
    source_document_id: int | None
    is_done: bool


class StageEventUpdate(BaseModel):
    is_done: bool


class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    internal_no: str
    client_name: str
    patent_name: str
    patent_type: PatentType
    application_no: str | None
    application_date: date | None
    current_stage: CaseStage
    agent: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class CaseDetailOut(CaseOut):
    stage_events: list[CaseStageEventOut] = []
    documents: list["DocumentOut"] = []
    deadlines: list["DeadlineOut"] = []
    files: list["CaseFileOut"] = []


# ---------- Case file (supporting materials, e.g. disclosure CAD drawings,
# drafted correction responses) ----------
class CaseFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    category: str
    round_no: str | None
    original_filename: str
    note: str | None
    uploaded_at: datetime


# ---------- Document ----------
class DocumentParseResult(BaseModel):
    """Draft extraction result returned before user confirmation; nothing persisted yet."""

    temp_file_path: str
    original_filename: str
    doc_type: DocType
    doc_variant: str | None
    raw_text: str
    issue_date: date | None
    application_no: str | None
    applicant_name: str | None
    patent_name: str | None
    patent_type: PatentType | None
    matched_case_id: int | None
    matched_case_internal_no: str | None
    suggested_deadlines: list["SuggestedDeadline"] = []


class SuggestedDeadline(BaseModel):
    deadline_type: str
    due_date: date | None
    rule_matched: bool
    note: str | None = None


class DocumentConfirm(BaseModel):
    temp_file_path: str
    original_filename: str
    doc_type: DocType
    doc_variant: str | None = None
    raw_text: str | None = None
    issue_date: date | None
    application_no: str | None
    applicant_name: str | None
    patent_name: str | None
    patent_type: PatentType | None
    case_id: int | None = None  # explicit override; else matched by application_no
    create_new_case_if_unmatched: bool = False


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int | None
    original_filename: str
    doc_type: DocType
    doc_variant: str | None
    issue_date: date | None
    application_no: str | None
    applicant_name: str | None
    patent_name: str | None
    patent_type: PatentType | None
    is_confirmed: bool
    created_at: datetime


# ---------- Deadline ----------
class DeadlineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    document_id: int | None
    deadline_type: str
    due_date: date
    status: DeadlineStatus
    completed_at: datetime | None
    note: str | None
    created_at: datetime


class DeadlineWithCaseOut(DeadlineOut):
    case_internal_no: str
    case_client_name: str
    case_patent_name: str


class DeadlineUpdate(BaseModel):
    status: DeadlineStatus | None = None
    note: str | None = None
    due_date: date | None = None


# ---------- Deadline Rule ----------
class DeadlineRuleCreate(BaseModel):
    doc_type: DocType
    doc_variant: str | None = None
    patent_type: PatentType | None = None
    deadline_type: str
    period_value: int
    period_unit: str  # "天" | "月"
    description: str | None = None
    is_active: bool = True
    is_verified: bool = False


class DeadlineRuleUpdate(BaseModel):
    doc_variant: str | None = None
    patent_type: PatentType | None = None
    deadline_type: str | None = None
    period_value: int | None = None
    period_unit: str | None = None
    description: str | None = None
    is_active: bool | None = None
    is_verified: bool | None = None


class DeadlineRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doc_type: DocType
    doc_variant: str | None
    patent_type: PatentType | None
    deadline_type: str
    period_value: int
    period_unit: str
    description: str | None
    is_active: bool
    is_verified: bool


CaseDetailOut.model_rebuild()
DocumentParseResult.model_rebuild()
