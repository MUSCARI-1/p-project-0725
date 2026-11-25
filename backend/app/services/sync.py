from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, insert, select

from ..extensions import db
from ..models import Policy, PolicyCategory, PolicyRegion
from . import transform


def upsert_policies(items: list[dict], synced_at: datetime | None = None) -> list[str]:
    synced_at = synced_at or datetime.now()
    items = list({it.get("plcyNo"): it for it in items if it.get("plcyNo")}.values())
    rows = [transform.to_policy_fields(it, synced_at) for it in items]
    rows = [r for r in rows if r["policy_id"]]
    if not rows:
        return []
    ids = [r["policy_id"] for r in rows]

    db.session.execute(delete(PolicyRegion).where(PolicyRegion.policy_id.in_(ids)))
    db.session.execute(delete(PolicyCategory).where(PolicyCategory.policy_id.in_(ids)))
    for r in rows:
        db.session.merge(Policy(**r))
    db.session.flush()

    region_rows = [
        {"policy_id": it["plcyNo"], "region_code": code}
        for it in items
        if it.get("plcyNo")
        for code in transform.parse_regions(it)
    ]
    category_rows = [
        {"policy_id": it["plcyNo"], "category": cat}
        for it in items
        if it.get("plcyNo")
        for cat in transform.parse_categories(it)
    ]
    if region_rows:
        db.session.execute(insert(PolicyRegion), region_rows)
    if category_rows:
        db.session.execute(insert(PolicyCategory), category_rows)
    db.session.commit()
    return ids


def prune_missing(keep_ids: set[str]) -> int:
    existing = set(db.session.scalars(select(Policy.policy_id)))
    stale = list(existing - keep_ids)
    for i in range(0, len(stale), 500):
        chunk = stale[i : i + 500]
        db.session.execute(delete(PolicyRegion).where(PolicyRegion.policy_id.in_(chunk)))
        db.session.execute(delete(PolicyCategory).where(PolicyCategory.policy_id.in_(chunk)))
        db.session.execute(delete(Policy).where(Policy.policy_id.in_(chunk)))
    db.session.commit()
    return len(stale)
