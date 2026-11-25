from flask import current_app, jsonify

from ..services import recommend as recommend_service
from ..services.validators import parse_recommend_request
from ..utils import json_body, today_kst
from . import bp


@bp.post("/recommend")
def recommend():
    cfg = current_app.config
    today = today_kst()
    profile = parse_recommend_request(json_body(), today, cfg["DEFAULT_PAGE_SIZE"], cfg["MAX_PAGE_SIZE"])
    return jsonify(recommend_service.recommend(profile, today, cfg["AI_BATCH_SIZE"]))
