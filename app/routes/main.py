from flask import Blueprint, current_app

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def hello_world():
    return f"Hello World! debug={current_app.config.get('DEBUG')}"
