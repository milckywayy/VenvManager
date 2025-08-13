from flask import Blueprint, render_template, request
import docker

from app.services.environment import create_docker_env

docker_client = docker.from_env()

creator_bp = Blueprint("creator", __name__, url_prefix="/creator")


@creator_bp.route("/docker", methods=["GET", "POST"])
def make_docker():
    if request.method == "POST":
        name = request.form.get("name")
        docker_image = request.form.get("docker_image")
        internal_ports = request.form.getlist("ports[][internal]")
        published_ports = request.form.getlist("ports[][published]")

        port_mappings = []
        for internal, published in zip(internal_ports, published_ports):
            if internal and published:
                port_mappings.append(
                    {"internal": int(internal), "published": int(published)}
                )

        create_docker_env(
            name=name,
            image=docker_image,
            ports=port_mappings,
        )

    images = docker_client.images.list()
    image_names = []
    for img in images:
        for tag in img.tags:
            image_names.append(tag)

    return render_template("creator/docker.html", images=image_names)
