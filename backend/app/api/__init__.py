from flask import Blueprint

bp = Blueprint("api", __name__, url_prefix="/api")

from . import chat, meta, policies, recommend, regions  # noqa: E402,F401
