import os
import libvirt
import docker

from app.runtime.environment import Environment
from app.models.status import EnvStatus
from app.utils.networking import (
    create_docker_network,
    remove_docker_network,
    create_network,
    remove_network,
)

docker_client = docker.from_env()
libvirt_client = libvirt.open(os.getenv("LIBVIRT_CLIENT"))


class Cluster:
    def __init__(self, name: str, cluster_id: int, cluster_db_id: int = None):
        self.name = name
        self.id = cluster_id
        self.db_id = cluster_db_id
        self.environments = []

        self.network_name = f"venvbr{self.id}"

        create_network(self.network_name, cluster_id)

        self.docker_network = create_docker_network(
            docker_client, self.network_name, self.id
        )

    def _all_env_running(self):
        for env in self.environments:
            print(env.status())
            if env.status() == EnvStatus.RUNNING:
                continue
            else:
                return False
        return True

    def add_environment(self, env: Environment):
        self.environments.append(env)

    def start(self):
        for env in self.environments:
            env.start()

    def restart(self):
        for env in self.environments:
            env.restart()

    def status(self) -> dict:
        return {env.display_name: env.status() for env in self.environments}

    def is_ready(self) -> bool:
        return self._all_env_running()

    def get_access_info(self) -> dict:
        return {env.name: env.get_access_info() for env in self.environments}

    def get_resource_usage(self) -> dict:
        total = {"memory": 0, "network": {"rx": 0, "tx": 0}}

        per_env = {}
        for env in self.environments:
            r = env.get_resource_usage()
            per_env[env.display_name] = r
            total["memory"] += int(r.get("memory", 0))
            total["network"]["rx"] += int(r.get("network", {}).get("rx", 0))
            total["network"]["tx"] += int(r.get("network", {}).get("tx", 0))
        return {"total": total, "environments": per_env}

    def destroy(self):
        for env in self.environments:
            env.destroy()

        remove_docker_network(self.docker_network)
        remove_network(self.network_name)
