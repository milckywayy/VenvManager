import time

from docker.client import DockerClient

from app import load_env
from app.model.docker_env import DockerEnvironment
from app.model.environment import Environment
from app.model.status import EnvStatus
from app.model.vm_env import VMEnvironment
from app.utils.networking import (
    get_bridge_name,
    create_docker_network,
    remove_docker_network,
)


class Cluster:
    def __init__(self, name: str, cluster_id: int):
        self.name = name
        self.id = cluster_id
        self.environments = []

        self.docker_client = DockerClient()
        self.bridge_name = get_bridge_name(self.id)
        self.docker_network = create_docker_network(
            self.docker_client, self.name, self.bridge_name, self.id
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

    def status(self) -> dict:
        return {env.name: env.status() for env in self.environments}

    def is_ready(self) -> bool:
        return self._all_env_running()

    def get_access_info(self) -> dict:
        return {env.name: env.get_access_info() for env in self.environments}

    def destroy(self):
        for env in self.environments:
            env.destroy()

        remove_docker_network(self.docker_network)


if __name__ == "__main__":
    load_env("../../")

    cluster = Cluster("test", 0)

    cluster.add_environment(
        DockerEnvironment(
            name="test1",
            image="www",
            index=len(cluster.environments),
            internal_ports=[80],
            published_ports=[5000],
            network=cluster.docker_network,
            cluster_id=cluster.id,
            args={"FLAG": "TEST123"},
        )
    )

    cluster.add_environment(
        DockerEnvironment(
            name="test2",
            image="ssh",
            index=len(cluster.environments),
            internal_ports=[22],
            published_ports=[5001],
            network=cluster.docker_network,
            cluster_id=cluster.id,
            args={"FLAG": "TEST123"},
        )
    )

    cluster.add_environment(
        VMEnvironment(
            name="windows1",
            template_name="/home/milckywayy/PycharmProjects/VenvManager/temp/windows_vm_template.xml",
            base_image_name="/var/lib/libvirt/images/win7pro.qcow2",
            internal_ports=[3389],
            published_ports=[2137],
            network_name=cluster.bridge_name,
            args={"FLAG": "TEST123"},
        )
    )

    cluster.start()

    while not cluster.is_ready():
        print("Waiting...")
        time.sleep(1)

    input("click to destroy...")

    cluster.destroy()
