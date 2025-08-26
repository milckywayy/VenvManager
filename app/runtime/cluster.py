import os
import time
import libvirt
import docker

from app import load_env
from app.runtime.docker_env import DockerEnvironment
from app.runtime.environment import Environment
from app.models.status import EnvStatus
from app.runtime.vm_env import VMEnvironment
from app.utils.networking import (
    create_docker_network,
    remove_docker_network,
    create_network,
    remove_network,
)

docker_client = docker.from_env()
libvirt_client = libvirt.open(os.getenv("LIBVIRT_CLIENT"))


class Cluster:
    def __init__(self, name: str, cluster_id: int):
        self.name = name
        self.id = cluster_id
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
        return {env.name: env.status() for env in self.environments}

    def is_ready(self) -> bool:
        return self._all_env_running()

    def get_access_info(self) -> dict:
        return {env.name: env.get_access_info() for env in self.environments}

    def destroy(self):
        for env in self.environments:
            env.destroy()

        remove_docker_network(self.docker_network)
        remove_network(self.network_name)


if __name__ == "__main__":
    load_env("../../")

    cluster = Cluster("cluster1", 0)
    cluster2 = Cluster("cluster2", 1)

    template = ""
    with open(
        "/home/milckywayy/PycharmProjects/VenvManager/temp/windows_vm_template.xml", "r"
    ) as f:
        template = f.read()

    cluster.add_environment(
        DockerEnvironment(
            docker_client,
            name="test1",
            image="www",
            internal_ports=[80, 22],
            published_ports=[5000, 5002],
            docker_network=cluster.docker_network,
            cluster_id=cluster.id,
        )
    )

    cluster.add_environment(
        DockerEnvironment(
            docker_client,
            name="test2",
            image="ssh",
            internal_ports=[22],
            published_ports=[5001],
            docker_network=cluster.docker_network,
            cluster_id=cluster.id,
        )
    )

    cluster.add_environment(
        VMEnvironment(
            libvirt_client,
            name="windows1",
            template=template,
            base_image_name="/var/lib/libvirt/images/win7pro.qcow2",
            internal_ports=[3389],
            published_ports=[2137],
            network_name=cluster.network_name,
        )
    )

    cluster2.add_environment(
        VMEnvironment(
            libvirt_client,
            name="windodasdaws1",
            template=template,
            base_image_name="/var/lib/libvirt/images/win7pro.qcow2",
            internal_ports=[3389],
            published_ports=[3137],
            network_name=cluster2.network_name,
        )
    )

    cluster2.add_environment(
        DockerEnvironment(
            docker_client,
            name="testxca",
            image="www",
            internal_ports=[80, 22],
            published_ports=[6000, 6002],
            docker_network=cluster2.docker_network,
            cluster_id=cluster2.id,
        )
    )

    cluster2.add_environment(
        DockerEnvironment(
            docker_client,
            name="testfafa2",
            image="ssh",
            internal_ports=[22],
            published_ports=[6001],
            docker_network=cluster2.docker_network,
            cluster_id=cluster2.id,
        )
    )

    cluster.start()
    cluster2.start()

    # while not cluster.is_ready() and not cluster2.is_ready():
    while not cluster.is_ready():
        print("Waiting...")
        time.sleep(1)

    input("click to destroy...")

    cluster.destroy()
    cluster2.destroy()
