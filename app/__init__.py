from flask import Flask
from app.routes.main import main_bp
from .config import config_map
from dotenv import load_dotenv
import os


def create_app():
    load_dotenv()

    app = Flask(__name__)
    env = os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config_map[env])

    app.register_blueprint(main_bp)

    return app
