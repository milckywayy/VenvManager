import os
import random

import psutil
from flask import blueprints, request, jsonify
import docker
import libvirt

from app.models import Cluster as ClusterModel
from app.runtime import Cluster, DockerEnvironment, VMEnvironment

api_bp = blueprints.Blueprint("api", __name__, url_prefix="/api")

docker_client = docker.from_env()
libvirt_client = libvirt.open(os.getenv("LIBVIRT_CLIENT"))
clusters = {}
available_ports = [
    port
    for port in range(
        int(os.getenv("ENV_PORTS_BEGIN")), int(os.getenv("ENV_PORTS_END"))
    )
]


@api_bp.route("/run/<int:cluster_id>", methods=["POST"])
def run(cluster_id: int):
    data = request.json
    session_id = data["session_id"]

    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    cluster_db = ClusterModel.query.filter_by(id=cluster_id).first()
    if not cluster_db:
        return jsonify({"error": "Cluster not found"}), 404

    environments_db = cluster_db.environments

    cluster = Cluster(
        name=f"{session_id}-{cluster_db.name}",
        cluster_id=int(session_id),
        cluster_db_id=cluster_db.id,
    )

    for env_db in environments_db:
        internal_ports = env_db.ports
        published_ports = []
        for _ in internal_ports:
            if not available_ports:
                return jsonify({"error": "No available ports"}), 500
            published_ports.append(random.choice(available_ports))

        if env_db.docker:
            cluster.add_environment(
                DockerEnvironment(
                    docker_client=docker_client,
                    name=f"{session_id}-{env_db.name}",
                    display_name=env_db.name,
                    image=env_db.docker.image,
                    internal_ports=internal_ports,
                    published_ports=published_ports,
                    access_info=env_db.access_info,
                    docker_network=cluster.docker_network,
                    cluster_id=cluster_id,
                )
            )
        elif env_db.vm:
            cluster.add_environment(
                VMEnvironment(
                    libvirt_client=libvirt_client,
                    name=f"{session_id}-{env_db.name}",
                    display_name=env_db.name,
                    template=env_db.vm.template,
                    base_image_name=env_db.vm.base_image_path.split("/")[-1],
                    internal_ports=internal_ports,
                    published_ports=published_ports,
                    access_info=env_db.access_info,
                    network_name=cluster.network_name,
                )
            )

    clusters[session_id] = cluster
    cluster.start()

    return jsonify({"status": "started", "access_info": cluster.get_access_info()}), 200


@api_bp.route("/status", methods=["POST"])
def status():
    data = request.json
    session_id = data["session_id"]

    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    cluster = clusters.get(session_id)
    if not cluster:
        return jsonify({"error": "Cluster not found"}), 404

    env_statuses = cluster.status()  # noqa: F841

    return jsonify(
        {
            "cluster_id": str(cluster.db_id),
        }
    ), 200


@api_bp.route("/restart", methods=["POST"])
def restart():
    data = request.json
    session_id = data["session_id"]

    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    cluster = clusters.get(session_id)
    if not cluster:
        return jsonify({"error": "Cluster is not running"}), 404

    cluster.restart()

    return jsonify({"status": "stopped"}), 200


@api_bp.route("/stop", methods=["POST"])
def remove():
    data = request.json
    session_id = data["session_id"]

    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    cluster = clusters.get(session_id)
    print(cluster)
    if not cluster:
        return jsonify({"error": "Cluster is not running"}), 404

    for env in cluster.environments:
        published_ports = []
        for port in env.published_ports:
            if port in published_ports:
                available_ports.append(port)
                published_ports.remove(port)

    cluster.destroy()
    del clusters[session_id]

    return jsonify({"status": "stopped"}), 200


@api_bp.route("/running_clusters", methods=["GET"])
def running_clusters():
    result = []
    for session_id, cluster in clusters.items():
        cluster_id = cluster.db_id
        cluster_db = ClusterModel.query.filter_by(id=cluster_id).first()
        cluster_name = cluster_db.name

        if not cluster_db:
            continue

        result.append(
            {
                "session_id": session_id,
                "cluster_name": cluster_name,
                "cluster_id": cluster_id,
            }
        )

    return jsonify(result), 200


@api_bp.route("/resources/summary", methods=["GET"])
def resources_summary():
    host_cpu_percent = psutil.cpu_percent(interval=0.1)
    vm = psutil.virtual_memory()
    net = psutil.net_io_counters()

    overall = {"cpu": host_cpu_percent, "memory": 0, "network": {"rx": 0, "tx": 0}}
    clusters_list = []

    for session_id, cluster in clusters.items():
        try:
            res = cluster.get_resource_usage()
            total = res.get("total", {})

            cluster_id = cluster.db_id
            cluster_db = ClusterModel.query.filter_by(id=cluster_id).first()

            clusters_list.append(
                {
                    "session_id": str(session_id),
                    "cluster_id": str(cluster_id),
                    "cluster_name": cluster_db.name,
                    "resources": total,
                }
            )

            overall["memory"] += int(total.get("memory", 0) or 0)
            overall["network"]["rx"] += int(total.get("network", {}).get("rx", 0) or 0)
            overall["network"]["tx"] += int(total.get("network", {}).get("tx", 0) or 0)
        except Exception as e:
            print(f"Failed to read resources for cluster {session_id}: {e}")
            continue

    payload = {
        "host": {
            "cpu_percent": host_cpu_percent,
            "memory_percent": float(vm.percent),
            "memory_total": int(vm.total),
            "network": {"rx": int(net.bytes_recv), "tx": int(net.bytes_sent)},
        },
        "overall": overall,
        "clusters": clusters_list,
    }
    return jsonify(payload), 200
