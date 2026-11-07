import hashlib
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..database import CASE_FILES_DIR, UPLOADS_DIR, get_db
from ..models import (
    Agent,
    Case,
    CaseStage,
    CaseStageEvent,
    Company,
    Deadline,
    DeadlineStatus,
    Document,
    PatentType,
)
from ..schemas import DocumentConfirm, DocumentOut, DocumentParseResult, SuggestedDeadline
from ..services import deadline_calc
from ..services.doc_parser import parse_document
from ..services.ocr_extract import extract_text
from ..services.case_utils import generate_internal_no
from ..services.company_utils import find_company_by_name, get_or_create_company
from ..services.patent_type import patent_type_from_application_no
from ..services.stage_mapping import stage_for_document, stage_rank
from ..services.twin import auto_link_twin

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _match_case(db: Session, application_no: str | None) -> Case | None:
    if not application_no:
        return None
    return db.query(Case).filter(Case.application_no == application_no).first()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _find_duplicate(
    db: Session,
    *,
    file_hash: str | None,
    dispatch_no: str | None,
    application_no: str | None,
    doc_type,
    doc_variant: str | None,
    issue_date,
) -> tuple[Document, str] | None:
    """The same notice already recorded? Checked strongest-first."""
    if file_hash:
        doc = db.query(Document).filter(Document.file_hash == file_hash).first()
        if doc:
            return doc, "文件内容完全相同"
    if dispatch_no:
        doc = db.query(Document).filter(Document.dispatch_no == dispatch_no).first()
        if doc:
            return doc, f"发文序号 {dispatch_no} 相同"
    if application_no and issue_date and doc_type:
        doc = (
            db.query(Document)
            .filter(
                Document.application_no == application_no,
                Document.doc_type == doc_type,
                Document.issue_date == issue_date,
                (Document.doc_variant == doc_variant)
                if doc_variant
                else Document.doc_variant.is_(None),
            )
            .first()
        )
        if doc:
            return doc, "申请号、文书类型、发文日都相同"
    return None


def _stage_from_notices(db: Session, case: Case) -> tuple[CaseStage, Document] | None:
    """The case's stage is decided by its official notices: the latest one
    (by issue date) that maps to a stage wins, so the result doesn't depend
    on the order the notices were uploaded in. Notices issued on the same
    day are ordered by how far along the prosecution their stage is."""
    best: tuple | None = None
    for doc in db.query(Document).filter(Document.case_id == case.id).all():
        stage = stage_for_document(doc.doc_type, doc.doc_variant)
        if stage is None:
            continue
        day = doc.issue_date or doc.created_at.date()
        key = (day, stage_rank(stage), doc.id)
        if best is None or key > best[0]:
            best = (key, stage, doc)
    return (best[1], best[2]) if best else None


@router.post("/parse", response_model=DocumentParseResult)
def parse_uploaded_document(file: UploadFile, db: Session = Depends(get_db)):
    suffix = Path(file.filename).suffix.lower()
    temp_name = f"{uuid.uuid4().hex}{suffix}"
    temp_path = UPLOADS_DIR / temp_name
    with temp_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    try:
        raw_text = extract_text(str(temp_path))
    except ValueError as exc:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    fields = parse_document(raw_text)
    matched_case = _match_case(db, fields["application_no"])
    matched_company: Company | None = (
        matched_case.company if matched_case and matched_case.company
        else find_company_by_name(db, fields["applicant_name"])
    )
    file_hash = _file_sha256(temp_path)
    found = _find_duplicate(
        db,
        file_hash=file_hash,
        dispatch_no=fields["dispatch_no"],
        application_no=fields["application_no"],
        doc_type=fields["doc_type"],
        doc_variant=fields["doc_variant"],
        issue_date=fields["issue_date"],
    )
    duplicate = found[0] if found else None

    suggested = deadline_calc.calculate_deadlines(
        db,
        doc_type=fields["doc_type"],
        doc_variant=fields["doc_variant"],
        patent_type=fields["patent_type"],
        issue_date=fields["issue_date"],
        raw_text=raw_text,
    )

    return DocumentParseResult(
        temp_file_path=str(temp_path),
        original_filename=file.filename,
        doc_type=fields["doc_type"],
        doc_variant=fields["doc_variant"],
        raw_text=raw_text,
        issue_date=fields["issue_date"],
        application_no=fields["application_no"],
        applicant_name=fields["applicant_name"],
        patent_name=fields["patent_name"],
        patent_type=fields["patent_type"],
        application_date=fields["application_date"],
        matched_case_id=matched_case.id if matched_case else None,
        matched_case_internal_no=matched_case.internal_no if matched_case else None,
        matched_company_id=matched_company.id if matched_company else None,
        matched_company_name=matched_company.name if matched_company else None,
        duplicate_document_id=duplicate.id if duplicate else None,
        duplicate_case_id=duplicate.case_id if duplicate else None,
        duplicate_case_internal_no=(
            duplicate.case.internal_no if duplicate and duplicate.case else None
        ),
        duplicate_reason=found[1] if found else None,
        dispatch_no=fields["dispatch_no"],
        suggested_deadlines=[SuggestedDeadline(**s) for s in suggested],
    )


@router.post("/confirm", response_model=DocumentOut)
def confirm_document(payload: DocumentConfirm, db: Session = Depends(get_db)):
    temp_path = Path(payload.temp_file_path)
    if not temp_path.exists():
        raise HTTPException(status_code=400, detail="临时文件不存在，请重新上传")

    if not payload.allow_duplicate:
        found = _find_duplicate(
            db,
            file_hash=_file_sha256(temp_path),
            dispatch_no=payload.dispatch_no,
            application_no=payload.application_no,
            doc_type=payload.doc_type,
            doc_variant=payload.doc_variant,
            issue_date=payload.issue_date,
        )
        if found:
            dup, reason = found
            where = f"（案件 {dup.case.internal_no}）" if dup.case else ""
            raise HTTPException(
                status_code=409,
                detail=f"这份通知书已经录入过{where}：{reason}。如确需再次录入，请选择「仍然录入」",
            )

    case: Case | None = None
    if payload.case_id is not None:
        case = db.get(Case, payload.case_id)
        if not case:
            raise HTTPException(status_code=404, detail="指定的案件不存在")
    else:
        case = _match_case(db, payload.application_no)
        if case is None and payload.create_new_case_if_unmatched:
            # Fixed before the case is built below, so the case gets it too.
            payload.patent_type = (
                patent_type_from_application_no(payload.application_no) or payload.patent_type
            )
            company: Company | None
            if payload.company_id is not None:
                company = db.get(Company, payload.company_id)
                if not company:
                    raise HTTPException(status_code=404, detail="指定的企业不存在")
            else:
                company = get_or_create_company(db, payload.applicant_name)
            new_case_agent = db.get(Agent, payload.agent_id) if payload.agent_id else None
            case = Case(
                internal_no=generate_internal_no(db),
                company_id=company.id if company else None,
                client_name=company.name if company else (payload.applicant_name or "待补充"),
                patent_name=payload.patent_name or "待补充",
                patent_type=payload.patent_type or PatentType.UNKNOWN,
                application_no=payload.application_no,
                application_date=payload.application_date,
                agent_id=new_case_agent.id if new_case_agent else None,
                agent=new_case_agent.name if new_case_agent else None,
                # It came from an official notice, so it has been filed
                # already; the notice's own stage mapping below moves it on.
                current_stage=CaseStage.FILED,
            )
            db.add(case)
            db.flush()
            db.add(
                CaseStageEvent(
                    case_id=case.id,
                    stage=case.current_stage,
                    note=f"根据文书「{payload.doc_type.value}」自动建案",
                )
            )
        elif case is None:
            raise HTTPException(
                status_code=400,
                detail="未能按申请号匹配到已有案件，请指定 case_id 或设置 create_new_case_if_unmatched=true",
            )

    # File the confirmed document away into the case's own folder (rather than
    # leaving it in the flat temp uploads pool) so browsing the case folder in
    # Explorer shows the official notices alongside any manually-added materials.
    file_hash = _file_sha256(temp_path)
    doc_dir = CASE_FILES_DIR / str(case.id) / "官方文书"
    doc_dir.mkdir(parents=True, exist_ok=True)
    final_path = doc_dir / f"{uuid.uuid4().hex}{temp_path.suffix}"
    shutil.move(str(temp_path), str(final_path))

    document = Document(
        case_id=case.id,
        file_path=str(final_path),
        original_filename=payload.original_filename,
        file_hash=file_hash,
        dispatch_no=payload.dispatch_no,
        doc_type=payload.doc_type,
        doc_variant=payload.doc_variant,
        raw_text=payload.raw_text,
        issue_date=payload.issue_date,
        application_no=payload.application_no,
        applicant_name=payload.applicant_name,
        patent_name=payload.patent_name,
        patent_type=payload.patent_type,
        application_date=payload.application_date,
        is_confirmed=True,
    )
    db.add(document)
    db.flush()

    # Fill in case fields the notice knows but the case doesn't yet (typical
    # for a case created from a disclosure, then the 受理通知书 arrives).
    if payload.application_no and not case.application_no:
        case.application_no = payload.application_no
    if payload.application_date and not case.application_date:
        case.application_date = payload.application_date
    derived_type = patent_type_from_application_no(case.application_no)
    if derived_type is not None:
        case.patent_type = derived_type
    elif payload.patent_type and case.patent_type == PatentType.UNKNOWN:
        case.patent_type = payload.patent_type
    if payload.patent_name and case.patent_name == "待补充":
        case.patent_name = payload.patent_name
    if case.company_id is None:
        company = get_or_create_company(db, payload.applicant_name)
        if company is not None:
            case.company_id = company.id
            case.client_name = company.name

    db.flush()
    # The notice may have just supplied the application date / type that
    # identifies this case's 双申 counterpart.
    auto_link_twin(db, case)
    decided = _stage_from_notices(db, case)
    if decided is not None and decided[0] != case.current_stage:
        new_stage, source = decided
        case.current_stage = new_stage
        db.add(
            CaseStageEvent(
                case_id=case.id,
                stage=new_stage,
                note=f"通知书「{source.doc_type.value}"
                + (f"（{source.doc_variant}）" if source.doc_variant else "")
                + "」"
                + (f"（发文日 {source.issue_date}）" if source.issue_date else ""),
                source_document_id=source.id,
            )
        )

    suggested = deadline_calc.calculate_deadlines(
        db,
        doc_type=payload.doc_type,
        doc_variant=payload.doc_variant,
        patent_type=payload.patent_type,
        issue_date=payload.issue_date,
        raw_text=payload.raw_text,
    )
    existing_deadlines = {
        (d.deadline_type, d.due_date) for d in case.deadlines if d.status == DeadlineStatus.PENDING
    }
    for item in suggested:
        if item["due_date"] is None:
            continue
        # 授予专利权通知书 and 办理登记手续通知书 arrive together and both carry
        # the registration deadline; list it once.
        if (item["deadline_type"], item["due_date"]) in existing_deadlines:
            continue
        existing_deadlines.add((item["deadline_type"], item["due_date"]))
        db.add(
            Deadline(
                case_id=case.id,
                document_id=document.id,
                deadline_type=item["deadline_type"],
                due_date=item["due_date"],
                note=item["note"],
            )
        )

    db.commit()
    db.refresh(document)
    return document
