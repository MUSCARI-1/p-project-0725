from flask import current_app, jsonify, request
from sqlalchemy import func, or_, select

from ..errors import invalid, not_found
from ..extensions import db
from ..models import Policy, PolicyCategory, PolicyRegion
from ..services import codes, regions, serializers
from ..utils import int_value, today_kst
from . import bp


@bp.get("/policies")
def list_policies():
    today = today_kst()
    args = request.args
    page = int_value(args.get("page"), "page", 1, 1, 10_000)
    size = int_value(args.get("size"), "size", current_app.config["DEFAULT_PAGE_SIZE"], 1, 100)

    q = select(Policy)
    if args.get("include_closed", "false").lower() != "true":
        q = q.where(serializers.not_closed_clause(today))
    if args.get("category"):
        cat = codes.normalize_category(args["category"])
        if cat not in codes.CATEGORIES:
            raise invalid(f"category 는 {', '.join(codes.CATEGORIES)} 중 하나여야 합니다.")
        q = q.where(Policy.policy_id.in_(select(PolicyCategory.policy_id).where(PolicyCategory.category == cat)))
    if args.get("region_code"):
        if not regions.is_valid(args["region_code"]):
            raise invalid(f"region_code '{args['region_code']}' 는 지역 목록에 없습니다. (GET /api/regions 참고)")
        match = regions.match_codes(args["region_code"])
        q = q.where(Policy.policy_id.in_(select(PolicyRegion.policy_id).where(PolicyRegion.region_code.in_(match))))
    if args.get("q"):
        like = f"%{args['q'].strip()}%"
        q = q.where(or_(Policy.name.like(like), Policy.keywords.like(like)))

    total = db.session.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.session.scalars(
        q.order_by(Policy.source_updated_at.desc(), Policy.policy_id.desc()).offset((page - 1) * size).limit(size)
    ).all()
    return jsonify(total=total, page=page, size=size, results=[serializers.policy_summary(p, today) for p in rows])


@bp.get("/policies/<policy_id>")
def get_policy(policy_id: str):
    p = db.session.get(Policy, policy_id)
    if p is None:
        raise not_found(f"정책을 찾을 수 없습니다: {policy_id}")
    regions = list(db.session.scalars(select(PolicyRegion.region_code).where(PolicyRegion.policy_id == policy_id)))
    categories = list(db.session.scalars(select(PolicyCategory.category).where(PolicyCategory.policy_id == policy_id)))
    return jsonify(serializers.policy_detail(p, today_kst(), regions, categories))
