from flask import Flask
from flask_cors import CORS

from .config import Config


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.json.ensure_ascii = False
    app.json.sort_keys = False

    from .extensions import db

    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    from . import models  # noqa: F401
    from .api import bp as api_bp
    from .cli import register_cli
    from .errors import register_error_handlers

    app.register_blueprint(api_bp)
    register_error_handlers(app)
    register_cli(app)
    return app
