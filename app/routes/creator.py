import os
from flask import Blueprint, render_template, request, abort, redirect, url_for, flash
import docker
import xml.etree.ElementTree as ET
import libvirt
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Cluster, Environment
from app.services.environment import (
    create_docker_env,
    create_vm_env,
    create_cluster_with_envs,
)

docker_client = docker.from_env()
libvirt_client = libvirt.open(os.getenv("LIBVIRT_CLIENT"))

creator_bp = Blueprint("creator", __name__, url_prefix="/creator")


@creator_bp.route("/docker", methods=["GET", "POST"])
def make_docker():
    if request.method == "POST":
        name = request.form.get("name")
        docker_image = request.form.get("docker_image")
        internal_ports = request.form.getlist("ports")
        access_info = request.form.get("access_info")

        ports = [int(p) for p in internal_ports if p.strip()]

        try:
            create_docker_env(
                name=name,
                image=docker_image,
                ports=ports,
                access_info=access_info,
            )
            flash(f"Docker environment '{name}' created successfully!", "success")
        except Exception as e:
            flash(f"Failed to create Docker environment: {e}", "danger")

    images = docker_client.images.list()
    image_names = []
    for img in images:
        for tag in img.tags:
            image_names.append(tag)

    return render_template(
        "creator/docker.html",
        images=image_names,
    )


@creator_bp.route("/vm", methods=["GET", "POST"])
def make_vm():
    if request.method == "POST":
        name = request.form.get("name")
        base_image_path = request.form.get("base_image_path")
        template = request.form.get("template")
        internal_ports = request.form.getlist("ports")
        access_info = request.form.get("access_info")

        ports = [int(p) for p in internal_ports if p.strip()]

        try:
            create_vm_env(
                name=name,
                template=template,
                base_image_path=base_image_path,
                ports=ports,
                access_info=access_info,
            )
            flash(f"VM environment '{name}' created successfully!", "success")
        except Exception as e:
            flash(f"Failed to create VM environment: {e}", "danger")

    images = {}
    for name in libvirt_client.listDefinedDomains():
        dom = libvirt_client.lookupByName(name)
        xml = dom.XMLDesc()
        tree = ET.fromstring(xml)

        for disk in tree.findall("./devices/disk"):
            if disk.get("device") != "disk":
                continue
            source = disk.find("source")
            if source is not None and "file" in source.attrib:
                images[name] = source.get("file")
                break

    return render_template("creator/vm.html", images=images)


@creator_bp.route("/cluster", methods=["GET", "POST"])
def make_cluster():
    message = None
    error = None

    if request.method == "POST":
        try:
            name = (request.form.get("name") or "").strip()
            env_ids = [int(x) for x in request.form.getlist("environment_ids")]

            if not name:
                raise ValueError("Cluster name is required.")
            if Cluster.query.filter_by(name=name).first():
                raise ValueError(f"Cluster named '{name}' already exists.")

            create_cluster_with_envs(name=name, environment_ids=env_ids)
            flash(f"Cluster '{name}' created successfully!", "success")

        except Exception as e:
            flash(f"Failed to create cluster: {e}", "danger")

    environments = (
        Environment.query.outerjoin(Environment.docker)
        .outerjoin(Environment.vm)
        .order_by(Environment.name.asc())
        .all()
    )

    return render_template(
        "creator/cluster.html",
        environments=environments,
        message=message,
        error=error,
    )


@creator_bp.route(
    "/creator/delete_env/<int:env_id>/<string:callback>", methods=["POST"]
)
def delete_env(env_id: int, callback: str):
    env = Environment.query.get(env_id)
    if not env:
        abort(404, description="Environment not found")

    try:
        db.session.delete(env)
        db.session.commit()
        flash(f"Environment '{env.name}' deleted successfully!", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Failed to delete environment (integrity error).", "danger")
        abort(400)

    allowed = {
        "main.index",
        "main.environments",
        "creator.make_docker",
        "creator.make_vm",
    }
    if callback not in allowed:
        abort(400, description="Forbidden callback")

    return redirect(url_for(callback))


@creator_bp.route(
    "/creator/delete_cluster/<int:cluster_id>/<string:callback>", methods=["POST"]
)
def delete_cluster(cluster_id: int, callback: str):
    cluster = Cluster.query.get(cluster_id)
    if not cluster:
        abort(404, description="Cluster not found")

    try:
        db.session.delete(cluster)
        db.session.commit()
        flash(f"Cluster '{cluster.name}' deleted successfully!", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Failed to delete cluster (integrity error).", "danger")
        abort(400)

    allowed = {"main.index", "creator.make_cluster"}
    if callback not in allowed:
        abort(400, description="Forbidden callback")

    return redirect(url_for(callback))
