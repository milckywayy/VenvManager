from docker.client import DockerClient

from app.runtime.environment import Environment
from app.models.status import EnvStatus
from docker.errors import ImageNotFound, APIError, DockerException, ContainerError
from docker.models.networks import Network
import logging


class DockerEnvException(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"DockerEnvException: {self.message}"


class DockerEnvironment(Environment):
    def __init__(
        self,
        docker_client: DockerClient,
        name: str,
        display_name: str,
        image: str,
        internal_ports: list,
        published_ports: list,
        variables: dict[str, str],
        access_info: str,
        docker_network: Network,
    ):
        super().__init__(
            name, display_name, internal_ports, published_ports, access_info
        )
        self.docker_client = docker_client
        self.image = image
        self.variables = variables
        self.docker_network = docker_network

        self.container = None
        logging.info(f"Created docker environment {name}")

    def _get_container_ip(self) -> str | None:
        if self.container is None:
            return None
        self.container.reload()

        nets = self.container.attrs.get("NetworkSettings", {}).get("Networks", {})
        net_name = self.docker_network.name
        if net_name in nets:
            return nets[net_name].get("IPAddress") or None  # IPv4
        for data in nets.values():
            if data.get("IPAddress"):
                return data["IPAddress"]
        return None

    def _on_started(self):
        self.ip = self._get_container_ip() or "unknown"

    def start(self):
        try:
            self.container = self.docker_client.containers.run(
                self.image,
                detach=True,
                ports={
                    f"{internal}/tcp": published
                    for internal, published in zip(
                        self.internal_ports, self.published_ports
                    )
                },
                network=self.docker_network.name,
                name=self.name,
                environment=self.variables,
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

        docker_status = self.docker_client.containers.get(self.container.id).status
        logging.debug(f"Checked docker {self.name} status: {docker_status}")
        return (
            EnvStatus(docker_status)
            if docker_status in EnvStatus._value2member_map_
            else EnvStatus.UNKNOWN
        )

    def get_resource_usage(self) -> dict:
        if self.container is None:
            return {"cpu": 0.0, "memory": 0, "network": {"rx": 0, "tx": 0}}

        try:
            stats = self.container.stats(stream=False)

            # --- Memory (bytes) ---
            mem_stats = stats.get("memory_stats", {}) or {}
            mem_usage = int(mem_stats.get("usage", 0) or 0)
            mem_cache = int((mem_stats.get("stats", {}) or {}).get("cache", 0) or 0)
            mem_real = max(0, mem_usage - mem_cache)

            # --- Network (bytes) ---
            networks = stats.get("networks") or {}
            rx = sum(int(v.get("rx_bytes", 0) or 0) for v in networks.values())
            tx = sum(int(v.get("tx_bytes", 0) or 0) for v in networks.values())

            return {"memory": mem_real, "network": {"rx": rx, "tx": tx}}

        except Exception as e:
            logging.exception(
                f"Failed to read docker resources for {getattr(self, 'name', 'unknown')}: {e}"
            )
            return {"cpu": 0.0, "memory": 0, "network": {"rx": 0, "tx": 0}}

    def destroy(self):
        if self.container is None:
            logging.warning(
                f"Tried to remove {self.name}, but environment was not started"
            )
            return

        self.container.stop()
        self.container.remove()

        logging.info(f"Removed docker environment {self.name}")
