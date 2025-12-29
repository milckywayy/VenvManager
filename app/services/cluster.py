from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import psutil

from app.models import Cluster as ClusterModel
from app.runtime import Cluster, DockerEnvironment, VMEnvironment
from app.services.ports import PortPool
from app.services.registry import ClusterRegistry


class NotFoundError(RuntimeError):
    pass


class ValidationError(RuntimeError):
    pass


@dataclass(frozen=True)
class RunResult:
    status: str
    access_info: Dict[str, Any]


class ClusterService:
    def __init__(
        self,
        *,
        registry: ClusterRegistry,
        port_pool: PortPool,
        docker_client,
        libvirt_client,
    ):
        self.registry = registry
        self.port_pool = port_pool
        self.docker_client = docker_client
        self.libvirt_client = libvirt_client

    def run(self, cluster_db_id: int, session_id: str) -> RunResult:
        if not session_id:
            raise ValidationError("session_id is required")

        cluster_db = ClusterModel.query.filter_by(id=cluster_db_id).first()
        if not cluster_db:
            raise NotFoundError("Cluster not found")

        envs_db = cluster_db.environments

        cluster = Cluster(
            name=f"{session_id}-{cluster_db.name}",
            cluster_id=int(session_id),
            cluster_db_id=cluster_db.id,
        )

        for env_db in envs_db:
            internal_ports = list(env_db.ports or [])
            published_ports = self.port_pool.allocate_many(len(internal_ports))

            if env_db.docker:
                cluster.add_environment(
                    DockerEnvironment(
                        docker_client=self.docker_client,
                        name=f"{session_id}-{env_db.name}",
                        display_name=env_db.name,
                        image=env_db.docker.image,
                        internal_ports=internal_ports,
                        published_ports=published_ports,
                        access_info=env_db.access_info,
                        docker_network=cluster.docker_network,
                        cluster_id=cluster_db_id,
                    )
                )
            elif env_db.vm:
                cluster.add_environment(
                    VMEnvironment(
                        libvirt_client=self.libvirt_client,
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

        self.registry.set(session_id, cluster)
        cluster.start()

        return RunResult(status="started", access_info=cluster.get_access_info())

    def status(self, session_id: str) -> Dict[str, Any]:
        if not session_id:
            raise ValidationError("session_id is required")

        cluster = self.registry.get(session_id)
        if not cluster:
            raise NotFoundError("Cluster not found")

        env_statuses = cluster.status()
        result = {name: st.value for name, st in env_statuses.items()}
        return {"cluster_id": str(cluster.db_id), "statuses": result}

    def access_info(self, session_id: str) -> Dict[str, Any]:
        if not session_id:
            raise ValidationError("session_id is required")

        cluster = self.registry.get(session_id)
        if not cluster:
            raise NotFoundError("Cluster not found")

        return {"access_info": cluster.get_access_info()}

    def restart(self, session_id: str) -> Dict[str, Any]:
        if not session_id:
            raise ValidationError("session_id is required")

        cluster = self.registry.get(session_id)
        if not cluster:
            raise NotFoundError("Cluster is not running")

        cluster.restart()
        return {"status": "stopped"}

    def stop(self, session_id: str) -> Dict[str, Any]:
        if not session_id:
            raise ValidationError("session_id is required")

        cluster = self.registry.pop(session_id)
        if not cluster:
            raise NotFoundError("Cluster is not running")

        used_ports: List[int] = []
        for env in cluster.environments:
            used_ports.extend(list(getattr(env, "published_ports", []) or []))
        self.port_pool.release_many(used_ports)

        cluster.destroy()
        return {"status": "stopped"}

    def running_clusters(self) -> List[Dict[str, Any]]:
        result = []
        for session_id, cluster in self.registry.items():
            cluster_id = cluster.db_id
            cluster_db = ClusterModel.query.filter_by(id=cluster_id).first()
            if not cluster_db:
                continue

            result.append(
                {
                    "session_id": session_id,
                    "cluster_name": cluster_db.name,
                    "cluster_id": cluster_id,
                }
            )
        return result

    def resources_summary(self) -> Dict[str, Any]:
        host_cpu_percent = psutil.cpu_percent(interval=0.1)
        vm = psutil.virtual_memory()
        net = psutil.net_io_counters()

        overall = {"cpu": host_cpu_percent, "memory": 0, "network": {"rx": 0, "tx": 0}}
        clusters_list = []

        for session_id, cluster in self.registry.items():
            try:
                res = cluster.get_resource_usage()
                total = res.get("total", {})

                cluster_id = cluster.db_id
                cluster_db = ClusterModel.query.filter_by(id=cluster_id).first()

                clusters_list.append(
                    {
                        "session_id": str(session_id),
                        "cluster_id": str(cluster_id),
                        "cluster_name": cluster_db.name if cluster_db else None,
                        "resources": total,
                    }
                )

                overall["memory"] += int(total.get("memory", 0) or 0)
                overall["network"]["rx"] += int(
                    total.get("network", {}).get("rx", 0) or 0
                )
                overall["network"]["tx"] += int(
                    total.get("network", {}).get("tx", 0) or 0
                )
            except Exception as e:
                print(f"Failed to read resources for cluster {session_id}: {e}")
                continue

        return {
            "host": {
                "cpu_percent": host_cpu_percent,
                "memory_percent": float(vm.percent),
                "memory_total": int(vm.total),
                "network": {"rx": int(net.bytes_recv), "tx": int(net.bytes_sent)},
            },
            "overall": overall,
            "clusters": clusters_list,
        }
