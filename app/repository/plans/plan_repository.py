from fastapi import Depends
from sqlmodel import Session
from app.repository.db import get_session_sync
from app.schema.plan import Plan


def save_plan(plan: Plan, session: Session = Depends(get_session_sync)):
    session.add(plan)
