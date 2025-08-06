import os

from flask import Blueprint

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def hello_world():
    return f"Hello World! debug={bool(int(os.getenv('DEBUG')))}"
