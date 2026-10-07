import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import CASE_FILES_DIR, get_db
from ..models import Case, CaseFile
from ..schemas import CaseFileOut

router = APIRouter(prefix="/api/cases", tags=["case-files"])


def _case_dir(case_id: int) -> Path:
    case_dir = CASE_FILES_DIR / str(case_id)
    case_dir.mkdir(parents=True, exist_ok=True)
    return case_dir


def _get_case_or_404(db: Session, case_id: int) -> Case:
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在")
    return case


def _get_case_file_or_404(db: Session, case_id: int, file_id: int) -> CaseFile:
    record = db.get(CaseFile, file_id)
    if not record or record.case_id != case_id:
        raise HTTPException(status_code=404, detail="文件不存在")
    return record


@router.post("/{case_id}/files", response_model=CaseFileOut)
def upload_case_file(
    case_id: int,
    file: UploadFile,
    category: str = Form(...),
    round_no: str | None = Form(None),
    note: str | None = Form(None),
    db: Session = Depends(get_db),
):
    _get_case_or_404(db, case_id)

    suffix = Path(file.filename).suffix
    stored_path = _case_dir(case_id) / f"{uuid.uuid4().hex}{suffix}"
    with stored_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    record = CaseFile(
        case_id=case_id,
        category=category,
        round_no=round_no,
        original_filename=file.filename,
        stored_path=str(stored_path),
        note=note,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/{case_id}/files", response_model=list[CaseFileOut])
def list_case_files(case_id: int, db: Session = Depends(get_db)):
    _get_case_or_404(db, case_id)
    return (
        db.query(CaseFile)
        .filter(CaseFile.case_id == case_id)
        .order_by(CaseFile.uploaded_at)
        .all()
    )


@router.get("/{case_id}/files/{file_id}/download")
def download_case_file(case_id: int, file_id: int, db: Session = Depends(get_db)):
    record = _get_case_file_or_404(db, case_id, file_id)
    if not Path(record.stored_path).exists():
        raise HTTPException(status_code=404, detail="文件已丢失（磁盘上找不到该文件）")
    return FileResponse(record.stored_path, filename=record.original_filename)


@router.delete("/{case_id}/files/{file_id}")
def delete_case_file(case_id: int, file_id: int, db: Session = Depends(get_db)):
    record = _get_case_file_or_404(db, case_id, file_id)
    Path(record.stored_path).unlink(missing_ok=True)
    db.delete(record)
    db.commit()
    return {"ok": True}


@router.post("/{case_id}/files/open-folder")
def open_case_folder(case_id: int, db: Session = Depends(get_db)):
    """Reveals the case's on-disk folder in Explorer, so files can also be
    dropped in directly rather than only through the upload button. Only
    meaningful when running as the desktop app on the same machine.
    """
    _get_case_or_404(db, case_id)
    case_dir = _case_dir(case_id)
    if os.name == "nt":
        os.startfile(case_dir)  # type: ignore[attr-defined]
    return {"ok": True, "path": str(case_dir)}
