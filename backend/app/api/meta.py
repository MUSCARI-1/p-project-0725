from flask import jsonify
from sqlalchemy import func, select, text

from ..extensions import db
from ..models import Policy
from ..services import codes
from . import bp


@bp.get("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return jsonify(status="ok" if db_ok else "degraded", db=db_ok), (200 if db_ok else 503)


@bp.get("/meta")
def meta():
    count, last_synced = db.session.execute(select(func.count(Policy.policy_id), func.max(Policy.synced_at))).one()
    return jsonify(
        enums=codes.REQUEST_ENUMS,
        policy_count=count,
        last_synced_at=last_synced.isoformat() if last_synced else None,
    )
