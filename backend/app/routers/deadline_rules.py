from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import DeadlineRule
from ..schemas import DeadlineRuleCreate, DeadlineRuleOut, DeadlineRuleUpdate

router = APIRouter(prefix="/api/deadline-rules", tags=["deadline-rules"])


@router.get("", response_model=list[DeadlineRuleOut])
def list_rules(db: Session = Depends(get_db)):
    return db.query(DeadlineRule).order_by(DeadlineRule.doc_type).all()


@router.post("", response_model=DeadlineRuleOut)
def create_rule(payload: DeadlineRuleCreate, db: Session = Depends(get_db)):
    rule = DeadlineRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.patch("/{rule_id}", response_model=DeadlineRuleOut)
def update_rule(rule_id: int, payload: DeadlineRuleUpdate, db: Session = Depends(get_db)):
    rule = db.get(DeadlineRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.get(DeadlineRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    db.delete(rule)
    db.commit()
    return {"ok": True}
