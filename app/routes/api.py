import os
from flask import blueprints, request, jsonify

from app.services.cluster import ClusterService, NotFoundError, ValidationError
from app.services.ports import PortPool, NoAvailablePortsError
from app.services.registry import ClusterRegistry
from app.services.clients import create_docker_client, create_libvirt_client

api_bp = blueprints.Blueprint("api", __name__, url_prefix="/api")

_registry = ClusterRegistry()
_port_pool = PortPool(
    range(int(os.getenv("ENV_PORTS_BEGIN")), int(os.getenv("ENV_PORTS_END")))
)
_service = ClusterService(
    registry=_registry,
    port_pool=_port_pool,
    docker_client=create_docker_client(),
    libvirt_client=create_libvirt_client(),
)


def _get_session_id():
    data = request.json or {}
    return data.get("session_id")


@api_bp.route("/run/<int:cluster_id>", methods=["POST"])
def run(cluster_id: int):
    try:
        session_id = _get_session_id()

        payload = request.get_json(silent=True) or {}
        variables = payload.get("variables", {})

        if variables is None:
            variables = {}
        if not isinstance(variables, dict):
            raise ValidationError("'variables' must be an object (dict).")

        for k, v in variables.items():
            if not isinstance(k, str) or not isinstance(v, str):
                raise ValidationError("All variables must be string->string.")

        result = _service.run(cluster_id, variables, session_id)
        return jsonify(
            {"status": result.status, "access_info": result.access_info}
        ), 200

    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except NoAvailablePortsError as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/status", methods=["POST"])
def status():
    try:
        return jsonify(_service.status(_get_session_id())), 200
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404


@api_bp.route("/access_info", methods=["POST"])
def access_info():
    try:
        return jsonify(_service.access_info(_get_session_id())), 200
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404


@api_bp.route("/restart", methods=["POST"])
def restart():
    try:
        return jsonify(_service.restart(_get_session_id())), 200
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404


@api_bp.route("/stop", methods=["POST"])
def stop():
    try:
        return jsonify(_service.stop(_get_session_id())), 200
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404


@api_bp.route("/extend_ttl", methods=["POST"])
def extend_ttl():
    try:
        session_id = _get_session_id()
        _service.extend_ttl(session_id)

        result = _service.status(session_id)
        return jsonify(
            {
                "status": "extended",
                "ttl_remaining_seconds": result["ttl_remaining_seconds"],
            }
        ), 200

    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404


@api_bp.route("/running_clusters", methods=["GET"])
def running_clusters():
    return jsonify(_service.running_clusters()), 200


@api_bp.route("/resources/summary", methods=["GET"])
def resources_summary():
    return jsonify(_service.resources_summary()), 200
