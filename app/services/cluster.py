from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime
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

        self.ttl_seconds = int(os.getenv("CLUSTER_TTL_SECONDS"))
        self._ttl_check_interval = int(os.getenv("CLUSTER_TTL_POLL_SECONDS"))
        threading.Thread(target=self._cleanup_loop, daemon=True).start()

    def _cleanup_loop(self):
        while True:
            for session_id in self.registry.expired_sessions():
                try:
                    self.stop(session_id)
                except NotFoundError:
                    pass
            time.sleep(self._ttl_check_interval)

    @staticmethod
    def _ttl_remaining_seconds(
        expires_at: datetime, now: datetime | None = None
    ) -> int:
        now = now or datetime.now()
        return max(0, int((expires_at - now).total_seconds()))

    def run(
        self, cluster_db_id: int, variables: dict[str, str], session_id: str
    ) -> RunResult:
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
                        variables=variables,
                        access_info=env_db.access_info,
                        docker_network=cluster.docker_network,
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

        self.registry.set(session_id, cluster, ttl_seconds=self.ttl_seconds)
        cluster.start()

        return RunResult(status="started", access_info=cluster.get_access_info())

    def status(self, session_id: str) -> Dict[str, Any]:
        if not session_id:
            raise ValidationError("session_id is required")

        entry = self.registry.get_entry(session_id)
        if not entry:
            raise NotFoundError("Cluster not found")

        cluster, _, expires_at = entry
        ttl_remaining = self._ttl_remaining_seconds(expires_at)

        env_statuses = cluster.status()
        result = {name: st.value for name, st in env_statuses.items()}
        return {
            "cluster_id": str(cluster.db_id),
            "ttl_remaining_seconds": ttl_remaining,
            "statuses": result,
        }

    def extend_ttl(self, session_id: str) -> None:
        if not session_id:
            raise ValidationError("session_id is required")

        entry = self.registry.get_entry(session_id)
        if not entry:
            raise NotFoundError("Cluster not found")

        cluster, created_at, expires_at = entry

        allow_extend_after = int(os.getenv("CLUSTER_TTL_ALLOW_EXTEND_TIME_SECONDS"))
        extend_by = int(os.getenv("CLUSTER_TTL_EXTEND_SECONDS"))

        if extend_by <= 0:
            return

        now = datetime.now()

        if allow_extend_after > 0:
            elapsed = int((now - created_at).total_seconds())
            if elapsed < allow_extend_after:
                raise ValidationError(
                    f"TTL can be extended after {allow_extend_after}s; "
                    f"try again in {allow_extend_after - elapsed}s"
                )

        self.registry.extend_ttl(session_id, extend_by)

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
        for session_id, (cluster, _, _) in self.registry.items():
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

        now = datetime.now()

        for session_id, (cluster, _, expires_at) in self.registry.items():
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
                        "ttl_remaining_seconds": self._ttl_remaining_seconds(
                            expires_at, now=now
                        ),
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
