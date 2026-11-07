import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class PatentType(str, enum.Enum):
    INVENTION = "发明专利"
    UTILITY_MODEL = "实用新型"
    DESIGN = "外观设计"
    UNKNOWN = "未知"


class CaseStage(str, enum.Enum):
    DISCLOSURE_PENDING_CONFIRM = "待确认"
    PENDING_DRAFTING = "待撰写"
    DRAFTING = "撰写中"
    FILED = "已提交申请"
    ACCEPTED = "已受理"
    PRELIM_EXAM = "初审合格"
    PUBLISHED = "已公布"
    SUBSTANTIVE_EXAM = "实质审查"
    FIRST_EXAM = "一审"
    SECOND_EXAM = "二审"
    THIRD_EXAM_PLUS = "三审及以后"
    CORRECTION = "补正"
    REEXAMINATION = "复审"
    INVALIDATION = "无效宣告"
    GRANTED = "授权"
    REGISTRATION = "缴费登记"
    COMPLETED = "已结案"
    REJECTED = "驳回"
    DEEMED_WITHDRAWN = "视为撤回"
    ABANDONED = "放弃"


class DocType(str, enum.Enum):
    DISCLOSURE = "交底书"
    RECEIPT_NOTICE = "受理通知书"
    FEE_PAYMENT_NOTICE = "缴纳申请费通知书"
    FEE_REDUCTION_NOTICE = "收费减缴审批通知书"
    PRELIM_EXAM_PASS_NOTICE = "初步审查合格通知书"
    PUBLICATION_NOTICE = "发明专利申请公布通知书"
    SUBSTANTIVE_EXAM_NOTICE = "进入实质审查阶段通知书"
    OFFICE_ACTION = "审查意见通知书"
    CORRECTION_NOTICE = "补正通知书"
    DEEMED_WITHDRAWN_NOTICE = "视为撤回通知书"
    REJECTION_DECISION = "驳回决定"
    REEXAM_NOTICE = "复审通知书"
    REEXAM_ACCEPTANCE_NOTICE = "复审请求受理通知书"
    INVALIDATION_NOTICE = "无效宣告请求受理通知书"
    INVALIDATION_DECISION = "无效宣告审查决定"
    GRANT_NOTICE = "授权通知书"
    REGISTRATION_NOTICE = "办理登记手续通知书"
    ANNUITY_NOTICE = "年费缴纳通知书"
    RESTORATION_NOTICE = "权利恢复相关通知书"
    OTHER = "其他"


class DeadlineStatus(str, enum.Enum):
    PENDING = "待处理"
    COMPLETED = "已完成"
    OVERDUE = "已超期"


class Agent(Base):
    """Patent attorney (专利代理人) roster. People can share a name, so the
    technical field and the 执业证号 are what tell them apart."""

    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    # 执业代理人 / 实习代理人 / 代理人助理 — trainees have no 执业证号 yet.
    role: Mapped[str] = mapped_column(String(20), default="执业代理人")
    field: Mapped[str | None] = mapped_column(String(100), nullable=True)
    license_no: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    phone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Left staff stay on their historical cases but can't be picked anymore.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Company(Base):
    """A client enterprise. Cases are organized under a company; the company
    name is also mirrored into Case.client_name so older code paths/filters
    that only know client_name keep working.
    """

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    credit_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contact_person: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    cases: Mapped[list["Case"]] = relationship(
        back_populates="company", order_by="Case.created_at.desc()"
    )


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    internal_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id"), nullable=True, index=True
    )
    client_name: Mapped[str] = mapped_column(String(200))
    patent_name: Mapped[str] = mapped_column(String(300))
    patent_type: Mapped[str] = mapped_column(
        Enum(PatentType, native_enum=False), default=PatentType.UNKNOWN
    )
    application_no: Mapped[str | None] = mapped_column(
        String(64), index=True, nullable=True
    )
    application_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    current_stage: Mapped[str] = mapped_column(
        Enum(CaseStage, native_enum=False), default=CaseStage.DISCLOSURE_PENDING_CONFIRM
    )
    # Responsible attorney. `agent` mirrors the roster name for display and
    # for cases entered before the roster existed.
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True, index=True)
    agent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # 一案双申 counterpart (invention <-> utility model filed the same day).
    # Kept symmetric: both cases point at each other.
    twin_case_id: Mapped[int | None] = mapped_column(
        ForeignKey("cases.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    company: Mapped["Company | None"] = relationship(back_populates="cases")
    stage_events: Mapped[list["CaseStageEvent"]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="CaseStageEvent.changed_at"
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="Document.created_at"
    )
    deadlines: Mapped[list["Deadline"]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="Deadline.due_date"
    )
    files: Mapped[list["CaseFile"]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="CaseFile.uploaded_at"
    )


class CaseStageEvent(Base):
    __tablename__ = "case_stage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    stage: Mapped[str] = mapped_column(Enum(CaseStage, native_enum=False))
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id"), nullable=True
    )
    is_done: Mapped[bool] = mapped_column(Boolean, default=False)

    case: Mapped["Case"] = relationship(back_populates="stage_events")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    file_path: Mapped[str] = mapped_column(String(500))
    original_filename: Mapped[str] = mapped_column(String(300))
    # sha256 of the file content, used to detect the same notice being
    # imported twice (e.g. re-importing a folder that was partly done before).
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # 发文序号: unique per notice CNIPA sends, so it identifies the same notice
    # even when the file itself differs (re-downloaded, re-scanned...).
    dispatch_no: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    doc_type: Mapped[str] = mapped_column(Enum(DocType, native_enum=False))
    doc_variant: Mapped[str | None] = mapped_column(String(50), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    application_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    applicant_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    patent_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    patent_type: Mapped[str | None] = mapped_column(
        Enum(PatentType, native_enum=False), nullable=True
    )
    application_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    case: Mapped["Case"] = relationship(back_populates="documents")
    deadlines: Mapped[list["Deadline"]] = relationship(back_populates="document")


class Deadline(Base):
    __tablename__ = "deadlines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id"), nullable=True
    )
    deadline_type: Mapped[str] = mapped_column(String(200))
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(
        Enum(DeadlineStatus, native_enum=False), default=DeadlineStatus.PENDING
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    case: Mapped["Case"] = relationship(back_populates="deadlines")
    document: Mapped["Document"] = relationship(back_populates="deadlines")


class CaseFile(Base):
    """Arbitrary supporting materials attached to a case — client-supplied
    disclosure materials (CAD drawings, etc.), drafted response documents,
    or anything else that isn't an official notice parsed via the
    documents/OCR pipeline. Stored on disk under a per-case folder so the
    folder can also be opened directly in Explorer.
    """

    __tablename__ = "case_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    category: Mapped[str] = mapped_column(String(100))
    round_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(300))
    stored_path: Mapped[str] = mapped_column(String(500))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    case: Mapped["Case"] = relationship(back_populates="files")


class DeadlineRule(Base):
    __tablename__ = "deadline_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doc_type: Mapped[str] = mapped_column(Enum(DocType, native_enum=False))
    doc_variant: Mapped[str | None] = mapped_column(String(50), nullable=True)
    patent_type: Mapped[str | None] = mapped_column(
        Enum(PatentType, native_enum=False), nullable=True
    )
    deadline_type: Mapped[str] = mapped_column(String(200))
    period_value: Mapped[int] = mapped_column(Integer)
    period_unit: Mapped[str] = mapped_column(String(10))  # "天" or "月"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
