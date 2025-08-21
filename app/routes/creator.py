import os
from flask import Blueprint, render_template, request
import docker
import xml.etree.ElementTree as ET
import libvirt

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


@creator_bp.route("/vm", methods=["GET", "POST"])
def make_vm():
    if request.method == "POST":
        name = request.form.get("name")
        base_image_path = request.form.get("base_image_path")
        template = request.form.get("template")
        internal_ports = request.form.getlist("ports[][internal]")
        published_ports = request.form.getlist("ports[][published]")

        port_mappings = []
        for internal, published in zip(internal_ports, published_ports):
            if internal and published:
                port_mappings.append(
                    {"internal": int(internal), "published": int(published)}
                )

        create_vm_env(
            name=name,
            template=template,
            base_image_path=base_image_path,
            ports=port_mappings,
        )

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
        name = (request.form.get("name") or "").strip()
        env_ids = [int(x) for x in request.form.getlist("environment_ids")]

        if not name:
            raise ValueError("Cluster name is required.")
        if Cluster.query.filter_by(name=name).first():
            raise ValueError(f"Cluster named '{name}' already exists.")

        create_cluster_with_envs(name=name, environment_ids=env_ids)

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
