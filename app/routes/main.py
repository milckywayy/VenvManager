from flask import Blueprint, render_template
from sqlalchemy.orm import joinedload

from app.models import Cluster, Environment

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    clusters = Cluster.query.join(Cluster.environments).all()
    return render_template("index.html", clusters=clusters)


@main_bp.route("/environments")
def environments():
    existing_environments = (
        Environment.query.options(
            joinedload(Environment.docker),
            joinedload(Environment.vm),
        )
        .order_by(Environment.name.asc())
        .all()
    )

    return render_template(
        "environments.html", existing_environments=existing_environments
    )


@main_bp.route("/base")
def base():
    return render_template("base.html")
