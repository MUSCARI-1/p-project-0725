from flask import jsonify

from ..errors import not_found
from ..extensions import db
from ..models import Policy
from ..services import ai_adapter, serializers
from ..services.validators import parse_chat_request
from ..utils import json_body
from . import bp


@bp.post("/chat")
def chat():
    req = parse_chat_request(json_body())
    policy = None
    if req["policy_id"]:
        p = db.session.get(Policy, req["policy_id"])
        if p is None:
            raise not_found(f"정책을 찾을 수 없습니다: {req['policy_id']}")
        policy = serializers.policy_for_ai(p)
    return jsonify(ai_adapter.answer_question(req["question"], policy, req["history"]))
