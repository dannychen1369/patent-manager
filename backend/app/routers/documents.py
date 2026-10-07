import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..database import CASE_FILES_DIR, UPLOADS_DIR, get_db
from ..models import Case, CaseStageEvent, Deadline, Document
from ..schemas import DocumentConfirm, DocumentOut, DocumentParseResult, SuggestedDeadline
from ..services import deadline_calc
from ..services.doc_parser import parse_document
from ..services.ocr_extract import extract_text
from ..services.case_utils import generate_internal_no
from ..services.stage_mapping import stage_for_document

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _match_case(db: Session, application_no: str | None) -> Case | None:
    if not application_no:
        return None
    return db.query(Case).filter(Case.application_no == application_no).first()


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

    suggested = deadline_calc.calculate_deadlines(
        db,
        doc_type=fields["doc_type"],
        doc_variant=fields["doc_variant"],
        patent_type=fields["patent_type"],
        issue_date=fields["issue_date"],
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
        matched_case_id=matched_case.id if matched_case else None,
        matched_case_internal_no=matched_case.internal_no if matched_case else None,
        suggested_deadlines=[SuggestedDeadline(**s) for s in suggested],
    )


@router.post("/confirm", response_model=DocumentOut)
def confirm_document(payload: DocumentConfirm, db: Session = Depends(get_db)):
    temp_path = Path(payload.temp_file_path)
    if not temp_path.exists():
        raise HTTPException(status_code=400, detail="临时文件不存在，请重新上传")

    case: Case | None = None
    if payload.case_id is not None:
        case = db.get(Case, payload.case_id)
        if not case:
            raise HTTPException(status_code=404, detail="指定的案件不存在")
    else:
        case = _match_case(db, payload.application_no)
        if case is None and payload.create_new_case_if_unmatched:
            case = Case(
                internal_no=generate_internal_no(db),
                client_name=payload.applicant_name or "待补充",
                patent_name=payload.patent_name or "待补充",
                patent_type=payload.patent_type,
                application_no=payload.application_no,
            )
            db.add(case)
            db.flush()
        elif case is None:
            raise HTTPException(
                status_code=400,
                detail="未能按申请号匹配到已有案件，请指定 case_id 或设置 create_new_case_if_unmatched=true",
            )

    # File the confirmed document away into the case's own folder (rather than
    # leaving it in the flat temp uploads pool) so browsing the case folder in
    # Explorer shows the official notices alongside any manually-added materials.
    doc_dir = CASE_FILES_DIR / str(case.id) / "官方文书"
    doc_dir.mkdir(parents=True, exist_ok=True)
    final_path = doc_dir / f"{uuid.uuid4().hex}{temp_path.suffix}"
    shutil.move(str(temp_path), str(final_path))

    document = Document(
        case_id=case.id,
        file_path=str(final_path),
        original_filename=payload.original_filename,
        doc_type=payload.doc_type,
        doc_variant=payload.doc_variant,
        raw_text=payload.raw_text,
        issue_date=payload.issue_date,
        application_no=payload.application_no,
        applicant_name=payload.applicant_name,
        patent_name=payload.patent_name,
        patent_type=payload.patent_type,
        is_confirmed=True,
    )
    db.add(document)
    db.flush()

    if payload.application_no and not case.application_no:
        case.application_no = payload.application_no

    new_stage = stage_for_document(payload.doc_type, payload.doc_variant)
    # Only log a stage-timeline entry when the stage actually changes —
    # otherwise uploading several documents that map to the same stage (e.g.
    # a batch of correction notices, all mapping to CORRECTION) spams the
    # timeline with duplicate no-op entries. The document itself is still
    # recorded in the documents list regardless.
    if new_stage is not None and new_stage != case.current_stage:
        case.current_stage = new_stage
        db.add(
            CaseStageEvent(
                case_id=case.id,
                stage=new_stage,
                note=f"上传文书「{payload.doc_type.value}」自动推进阶段",
                source_document_id=document.id,
            )
        )

    suggested = deadline_calc.calculate_deadlines(
        db,
        doc_type=payload.doc_type,
        doc_variant=payload.doc_variant,
        patent_type=payload.patent_type,
        issue_date=payload.issue_date,
    )
    for item in suggested:
        if item["due_date"] is None:
            continue
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
