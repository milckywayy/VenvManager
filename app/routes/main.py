from flask import Blueprint, render_template

from app.models import Cluster

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    clusters = Cluster.query.join(Cluster.environments).all()
    return render_template("index.html", clusters=clusters)


@main_bp.route("/base")
def base():
    return render_template("base.html")
