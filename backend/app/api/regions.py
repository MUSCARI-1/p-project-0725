from flask import jsonify

from ..services import regions
from . import bp


@bp.get("/regions")
def list_regions():
    return jsonify(regions=regions.load())
