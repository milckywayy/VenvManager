import os
from flask import Blueprint, render_template, request, abort, redirect, url_for, flash
from sqlalchemy.exc import IntegrityError

import docker
import libvirt

from app.services.creator import (
    CreatorService,
    CreateDockerEnvCmd,
    CreateVMEnvCmd,
    CreateClusterCmd,
    ValidationError,
    AlreadyExistsError,
    NotFoundError,
)
from app.services.repository import (
    ClusterRepository,
    EnvironmentRepository,
    ClusterEnvironmentRepository,
)
from app.services.environment_catalog import EnvironmentCatalog


creator_bp = Blueprint("creator", __name__, url_prefix="/creator")

docker_client = docker.from_env()
libvirt_client = libvirt.open(os.getenv("LIBVIRT_CLIENT"))

catalog = EnvironmentCatalog(docker_client=docker_client, libvirt_client=libvirt_client)
service = CreatorService(
    clusters=ClusterRepository(),
    envs=EnvironmentRepository(),
    links=ClusterEnvironmentRepository(),
)


def _ports_from_form() -> list[int]:
    internal_ports = request.form.getlist("ports")
    return [int(p) for p in internal_ports if (p or "").strip()]


@creator_bp.route("/docker", methods=["GET", "POST"])
def make_docker():
    if request.method == "POST":
        try:
            cmd = CreateDockerEnvCmd(
                name=request.form.get("name") or "",
                image=request.form.get("docker_image") or "",
                ports=_ports_from_form(),
                access_info=request.form.get("access_info") or "",
            )
            env = service.create_docker_env(cmd)
            flash(f"Docker environment '{env.name}' created successfully!", "success")
        except ValidationError as e:
            flash(str(e), "danger")
        except Exception as e:
            flash(f"Failed to create Docker environment: {e}", "danger")

    return render_template(
        "creator/docker.html",
        images=catalog.list_docker_image_tags(),
    )


@creator_bp.route("/vm", methods=["GET", "POST"])
def make_vm():
    if request.method == "POST":
        try:
            cmd = CreateVMEnvCmd(
                name=request.form.get("name") or "",
                base_image_path=request.form.get("base_image_path") or "",
                template=request.form.get("template") or "",
                ports=_ports_from_form(),
                access_info=request.form.get("access_info") or "",
            )
            env = service.create_vm_env(cmd)
            flash(f"VM environment '{env.name}' created successfully!", "success")
        except ValidationError as e:
            flash(str(e), "danger")
        except Exception as e:
            flash(f"Failed to create VM environment: {e}", "danger")

    return render_template("creator/vm.html", images=catalog.list_vm_images())


@creator_bp.route("/cluster", methods=["GET", "POST"])
def make_cluster():
    if request.method == "POST":
        try:
            name = (request.form.get("name") or "").strip()
            env_ids = [int(x) for x in request.form.getlist("environment_ids")]

            cmd = CreateClusterCmd(name=name, environment_ids=env_ids)
            cluster = service.create_cluster_with_envs(cmd)
            flash(f"Cluster '{cluster.name}' created successfully!", "success")

        except (ValidationError, AlreadyExistsError) as e:
            flash(str(e), "danger")
        except Exception as e:
            flash(f"Failed to create cluster: {e}", "danger")

    environments = service.envs.list_all_for_creator()
    return render_template(
        "creator/cluster.html", environments=environments, message=None, error=None
    )


@creator_bp.route(
    "/creator/delete_env/<int:env_id>/<string:callback>", methods=["POST"]
)
def delete_env(env_id: int, callback: str):
    allowed = {
        "main.index",
        "main.environments",
        "creator.make_docker",
        "creator.make_vm",
    }
    if callback not in allowed:
        abort(400, description="Forbidden callback")

    try:
        service.delete_environment(env_id)
        flash("Environment deleted successfully!", "success")
    except NotFoundError:
        abort(404, description="Environment not found")
    except IntegrityError:
        flash("Failed to delete environment (integrity error).", "danger")
        abort(400)

    return redirect(url_for(callback))


@creator_bp.route(
    "/creator/delete_cluster/<int:cluster_id>/<string:callback>", methods=["POST"]
)
def delete_cluster(cluster_id: int, callback: str):
    allowed = {"main.index", "main.clusters", "creator.make_cluster"}
    if callback not in allowed:
        abort(400, description="Forbidden callback")

    try:
        service.delete_cluster(cluster_id)
        flash("Cluster deleted successfully!", "success")
    except NotFoundError:
        abort(404, description="Cluster not found")
    except IntegrityError:
        flash("Failed to delete cluster (integrity error).", "danger")
        abort(400)

    return redirect(url_for(callback))
