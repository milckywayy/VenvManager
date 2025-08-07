from app.utils.networking import (
    create_docker_network,
    remove_docker_network,
    get_bridge_name,
    get_host_ip_address,
)
from environment import Environment
from app.model.status import EnvStatus
import docker
from docker.errors import ImageNotFound, APIError, DockerException, ContainerError
from docker.models.networks import Network
import logging
from app.config import Config

docker_client = docker.from_env()


class DockerEnvException(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"DockerEnvException: {self.message}"


class DockerEnvironment(Environment):
    def __init__(
        self,
        name: str,
        image: str,
        index: int,
        internal_ports: list,
        published_ports: list,
        network: Network,
        cluster_id: int,
        args: dict,
    ):
        super().__init__(name, internal_ports, published_ports, args)
        self.image = image
        self.index = index
        self.network = network
        self.cluster_id = cluster_id

        self.ip = get_host_ip_address(
            self.cluster_id, self.index + Config.DOCKER_IP_OFFSET
        )

        self.container = None
        logging.info(f"Created docker environment {name}")

    def _on_started(self):
        if self.container is None:
            logging.warning(
                f"Tried to stop {self.name}, but environment was not started"
            )
            return

        self.network.connect(self.container.id, ipv4_address=self.ip)
        logging.debug(
            f"Docker {self.name} has connected to network {self.network.name} with id {self.container.id}"
        )

    def start(self):
        try:
            self.container = docker_client.containers.run(
                self.image,
                detach=True,
                ports={
                    f"{internal}/tcp": published
                    for internal, published in zip(
                        self.internal_ports, self.published_ports
                    )
                },
                name=self.name,
                environment={**self.args},
            )
            logging.info(f"Started docker environment {self.name}")

            self._on_started()

        except ImageNotFound:
            msg = f"Docker environment {self.image} not found"
            logging.error(msg)
            raise DockerEnvException(msg)
        except ContainerError as e:
            msg = f"Docker environment {self.name} failed: {e}"
            logging.error(msg)
            raise DockerEnvException(msg)
        except APIError as e:
            msg = f"Docker environment {self.name} API error: {e}"
            logging.error(msg)
            raise DockerEnvException(msg)
        except DockerException as e:
            msg = f"Docker environment {self.name} error: {e}"
            logging.error(msg)
            raise DockerEnvException(msg)

    def stop(self):
        if self.container is None:
            logging.warning(
                f"Tried to stop {self.name}, but environment was not started"
            )
            raise DockerEnvException(f"Docker {self.name} has not started yet")

        self.container.stop()
        logging.info(f"Stopped docker environment {self.name}")

    def restart(self):
        if self.container is None:
            logging.warning(
                f"Tried to restart {self.name}, but environment was not started"
            )
            raise DockerEnvException(f"Docker {self.name} has not started yet")

        try:
            self.container.restart()
            logging.info(f"Restarted docker environment {self.name}")

        except ImageNotFound as e:
            logging.error(f"Docker environment {self.name} not found: {e}")
            raise DockerEnvException(f"Docker environment {self.name} not found: {e}")

    def status(self) -> EnvStatus:
        if self.container is None:
            return EnvStatus.UNKNOWN

        docker_status = docker_client.containers.get(self.container.id).status
        logging.debug(f"Checked docker {self.name} status: {docker_status}")
        return (
            EnvStatus(docker_status)
            if docker_status in EnvStatus._value2member_map_
            else EnvStatus.UNKNOWN
        )

    def get_access_info(self) -> dict:
        if self.container is None:
            logging.warning(
                f"Tried to stop {self.name}, but environment was not started"
            )
            raise DockerEnvException(f"Docker environment {self.name} was not started")

        logging.debug(f"Getting docker access info {self.name}")
        return {}

    def destroy(self):
        if self.container is None:
            logging.warning(
                f"Tried to remove {self.name}, but environment was not started"
            )
            return

        self.container.stop()
        self.container.remove()

        logging.info(f"Removed docker environment {self.name}")


if __name__ == "__main__":
    cluster_id = 100
    bridge_name = get_bridge_name(cluster_id)
    network_name = "docker-test"

    docker_network = create_docker_network(
        docker_client, network_name, bridge_name, cluster_id
    )
    print(docker_network)
    print(docker_client.images.list())

    container1 = DockerEnvironment(
        name="test1",
        image="www",
        index=0,
        internal_ports=[80],
        published_ports=[5000],
        network=docker_network,
        cluster_id=cluster_id,
        args={"FLAG": "TEST123"},
    )

    container2 = DockerEnvironment(
        name="test2",
        image="ssh",
        index=1,
        internal_ports=[22],
        published_ports=[5001],
        network=docker_network,
        cluster_id=cluster_id,
        args={"FLAG": "TEST123"},
    )
    print(container2)

    container1.start()
    # container1.on_started()

    container2.start()
    # container2.on_started()

    input("Press Enter to remove container...")

    container1.destroy()
    container2.destroy()

    remove_docker_network(docker_network)
