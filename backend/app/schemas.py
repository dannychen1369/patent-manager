from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from .models import CaseStage, DeadlineStatus, DocType, PatentType


# ---------- Agent (专利代理人) ----------
class AgentCreate(BaseModel):
    name: str
    role: str = "执业代理人"
    field: str | None = None
    license_no: str | None = None
    phone: str | None = None
    email: str | None = None
    notes: str | None = None
    is_active: bool = True


class AgentUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    field: str | None = None
    license_no: str | None = None
    phone: str | None = None
    email: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    role: str
    field: str | None
    license_no: str | None
    phone: str | None
    email: str | None
    notes: str | None
    is_active: bool
    created_at: datetime
    case_count: int = 0


# ---------- Company ----------
class CompanyCreate(BaseModel):
    name: str
    credit_code: str | None = None
    contact_person: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    address: str | None = None
    notes: str | None = None


class CompanyUpdate(BaseModel):
    name: str | None = None
    credit_code: str | None = None
    contact_person: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    address: str | None = None
    notes: str | None = None


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    credit_code: str | None
    contact_person: str | None
    contact_phone: str | None
    contact_email: str | None
    address: str | None
    notes: str | None
    created_at: datetime
    case_count: int = 0
    pending_deadline_count: int = 0


class CompanyDetailOut(CompanyOut):
    cases: list["CaseOut"] = []


# ---------- Case ----------
class CaseCreate(BaseModel):
    # Either pick an existing company (company_id) or give a name, in which
    # case a company of that name is found or created automatically.
    company_id: int | None = None
    client_name: str | None = None
    patent_name: str
    patent_type: PatentType = PatentType.UNKNOWN
    application_no: str | None = None
    application_date: date | None = None
    agent_id: int | None = None
    agent: str | None = None
    notes: str | None = None


class CaseUpdate(BaseModel):
    company_id: int | None = None
    client_name: str | None = None
    patent_name: str | None = None
    patent_type: PatentType | None = None
    application_no: str | None = None
    application_date: date | None = None
    agent_id: int | None = None
    agent: str | None = None
    notes: str | None = None


class TwinLink(BaseModel):
    twin_case_id: int


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
    company_id: int | None
    client_name: str
    patent_name: str
    patent_type: PatentType
    application_no: str | None
    application_date: date | None
    current_stage: CaseStage
    agent_id: int | None = None
    agent: str | None
    notes: str | None
    twin_case_id: int | None = None
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
    application_date: date | None = None
    matched_case_id: int | None
    matched_case_internal_no: str | None
    matched_company_id: int | None = None
    matched_company_name: str | None = None
    # Set when exactly this file (same content hash) was already recorded.
    duplicate_document_id: int | None = None
    duplicate_case_id: int | None = None
    duplicate_case_internal_no: str | None = None
    duplicate_reason: str | None = None
    dispatch_no: str | None = None
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
    application_date: date | None = None
    case_id: int | None = None  # explicit override; else matched by application_no
    create_new_case_if_unmatched: bool = False
    # Company for a newly-created case; if omitted, the company is found or
    # created from applicant_name.
    company_id: int | None = None
    dispatch_no: str | None = None
    # Responsible attorney for a newly-created case.
    agent_id: int | None = None
    # Save even though the same notice is already recorded.
    allow_duplicate: bool = False


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
    application_date: date | None = None
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


CompanyDetailOut.model_rebuild()
CaseDetailOut.model_rebuild()
DocumentParseResult.model_rebuild()
