import logging
from flask import Flask
from app.routes.main import main_bp
from app.utils.logging import setup_logging
from app.load_env import load_env
import os


def create_app():
    try:
        load_env()

    except EnvironmentError as e:
        logging.error(e)
        exit(1)

    print(os.getenv("SECRET_KEY"))

    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))
    setup_logging(bool(int(os.environ.get("DEBUG"))))

    app.register_blueprint(main_bp)

    return app
