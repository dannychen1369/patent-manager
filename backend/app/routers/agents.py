from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Agent, Case
from ..schemas import AgentCreate, AgentOut, AgentUpdate

router = APIRouter(prefix="/api/agents", tags=["agents"])


def _get_or_404(db: Session, agent_id: int) -> Agent:
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="代理人不存在")
    return agent


def _check_unique(db: Session, data: dict, exclude_id: int | None = None) -> None:
    license_no = (data.get("license_no") or "").strip()
    if license_no:
        q = db.query(Agent).filter(Agent.license_no == license_no)
        if exclude_id is not None:
            q = q.filter(Agent.id != exclude_id)
        if q.first():
            raise HTTPException(status_code=400, detail=f"执业证号 {license_no} 已存在")
    # Same name is allowed (同名同姓), but then something must tell them apart.
    name = (data.get("name") or "").strip()
    if name:
        field = data.get("field") or None
        q = db.query(Agent).filter(
            Agent.name == name,
            Agent.role == (data.get("role") or "执业代理人"),
            Agent.field.is_(None) if field is None else Agent.field == field,
            Agent.license_no.is_(None) if not license_no else Agent.license_no == license_no,
        )
        if exclude_id is not None:
            q = q.filter(Agent.id != exclude_id)
        if q.first():
            raise HTTPException(
                status_code=400,
                detail=f"已有同名代理人「{name}」，请填写不同的技术领域、身份或执业证号以便区分",
            )


def _out(agent: Agent, counts: dict[int, int]) -> AgentOut:
    out = AgentOut.model_validate(agent)
    out.case_count = counts.get(agent.id, 0)
    return out


def _case_counts(db: Session) -> dict[int, int]:
    return dict(
        db.query(Case.agent_id, func.count(Case.id))
        .filter(Case.agent_id.is_not(None))
        .group_by(Case.agent_id)
        .all()
    )


@router.get("", response_model=list[AgentOut])
def list_agents(include_inactive: bool = False, db: Session = Depends(get_db)):
    query = db.query(Agent)
    if not include_inactive:
        query = query.filter(Agent.is_active.is_(True))
    counts = _case_counts(db)
    return [_out(a, counts) for a in query.order_by(Agent.name, Agent.id).all()]


@router.post("", response_model=AgentOut)
def create_agent(payload: AgentCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["name"] = data["name"].strip()
    if not data["name"]:
        raise HTTPException(status_code=400, detail="请填写代理人姓名")
    data["license_no"] = (data.get("license_no") or "").strip() or None
    data["field"] = (data.get("field") or "").strip() or None
    _check_unique(db, data)
    agent = Agent(**data)
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return _out(agent, {})


@router.patch("/{agent_id}", response_model=AgentOut)
def update_agent(agent_id: int, payload: AgentUpdate, db: Session = Depends(get_db)):
    agent = _get_or_404(db, agent_id)
    data = payload.model_dump(exclude_unset=True)
    for key in ("name", "license_no", "field"):
        if key in data:
            data[key] = (data[key] or "").strip() or None
    if "name" in data and not data["name"]:
        raise HTTPException(status_code=400, detail="请填写代理人姓名")
    merged = {
        "name": data.get("name", agent.name),
        "role": data.get("role", agent.role),
        "field": data.get("field", agent.field),
        "license_no": data.get("license_no", agent.license_no),
    }
    _check_unique(db, merged, exclude_id=agent.id)
    for field, value in data.items():
        setattr(agent, field, value)
    # Keep the name shown on each case in step with the roster.
    for case in db.query(Case).filter(Case.agent_id == agent.id).all():
        case.agent = agent.name
    db.commit()
    db.refresh(agent)
    return _out(agent, _case_counts(db))


@router.delete("/{agent_id}")
def delete_agent(agent_id: int, db: Session = Depends(get_db)):
    agent = _get_or_404(db, agent_id)
    in_use = db.query(func.count(Case.id)).filter(Case.agent_id == agent.id).scalar()
    if in_use:
        raise HTTPException(
            status_code=400,
            detail=f"该代理人仍是 {in_use} 个案件的承办人，不能删除；如已离职，请改为「停用」",
        )
    db.delete(agent)
    db.commit()
    return {"ok": True}
