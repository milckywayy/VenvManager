from flask import Flask
from app.routes.main import main_bp
from .config import config_map
from dotenv import load_dotenv
from app.utils.logging import setup_logging
import os


def create_app():
    load_dotenv()

    app = Flask(__name__)
    env = os.getenv("FLASK_ENV", "development")
    app.config.from_object(config_map[env])
    setup_logging(app.config["DEBUG"])

    app.register_blueprint(main_bp)

    return app
