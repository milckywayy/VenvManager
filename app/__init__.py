import logging
from flask import Flask
from flask_migrate import Migrate
import os

from app.load_env import load_env
from app.routes.main import main_bp
from app.routes.creator import creator_bp
from app.utils.logging import setup_logging
from .extensions import db
from .routes.api import api_bp

migrate = Migrate()


def _build_db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    user = os.getenv("DB_USER", "postgres")
    pwd = os.getenv("DB_PASSWORD", "")
    name = os.getenv("DB_NAME", user)
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{name}"


def create_app() -> Flask:
    try:
        load_env()

    except EnvironmentError as e:
        logging.error(e)
        raise RuntimeError("Environment not configured") from e

    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))
    setup_logging(bool(int(os.environ.get("DEBUG"))))

    app.config["SQLALCHEMY_DATABASE_URI"] = _build_db_url()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    db.init_app(app)
    with app.app_context():
        from app.models import environment  # noqa: F401
    migrate.init_app(app, db)

    return app


def create_app_admin():
    app = create_app()

    app.register_blueprint(main_bp)
    app.register_blueprint(creator_bp)
    app.register_blueprint(api_bp)

    return app


def create_app_api():
    app = create_app()

    app.register_blueprint(api_bp)

    return app
