from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import Case


def generate_internal_no(db: Session) -> str:
    year = date.today().year
    prefix = f"C{year}-"
    count = (
        db.query(func.count(Case.id))
        .filter(Case.internal_no.like(f"{prefix}%"))
        .scalar()
    )
    return f"{prefix}{count + 1:04d}"
