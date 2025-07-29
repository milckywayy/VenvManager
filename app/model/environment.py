from abc import ABC, abstractmethod
from datetime import datetime
import docker
from docker.errors import ImageNotFound, APIError, DockerException, ContainerError
from app.model.status import EnvStatus
from flask import current_app

client = docker.from_env()


class Environment(ABC):
    def __init__(self, name: str, exposed_ports: list, host_ports: list, args: dict):
        # TODO add network parsing
        self.name = name

        if len(host_ports) == 0 or len(host_ports) != len(exposed_ports):
            raise ValueError("Ports and exposed ports must have same length.")

        self.host_ports = host_ports
        self.exposed_ports = exposed_ports
        self.args = args

        self.creation_time = datetime.now()

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def on_started(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def restart(self):
        pass

    @abstractmethod
    def status(self):
        pass

    @abstractmethod
    def get_access_info(self):
        pass

    @abstractmethod
    def destroy(self):
        pass

    def get_time_left(self):
        now = datetime.now()
        elapsed = (now - self.creation_time).total_seconds()
        remaining = current_app.config.get('ENV_TTL') - elapsed
        return max(0, int(remaining))

    def is_expired(self):
        return self.get_time_left() <= 0


class DockerEnvironment(Environment):
    def __init__(
        self,
        name: str,
        image: str,
        exposed_ports: list,
        host_ports: list,
        args: dict
    ):
        super().__init__(name, exposed_ports, host_ports, args)
        self.image = image

        self.container = None

    def start(self):
        try:
            self.container = client.containers.run(
                self.image,
                detach=True,
                ports={f'{exposed_port}/tcp': host_port for exposed_port, host_port in
                       zip(self.host_ports, self.exposed_ports)},
                name=self.name,
                environment={**self.args},
            )
        # TODO replace prints with custom exception
        except ImageNotFound:
            print(f"Error: Docker image '{self.image}' not found.")
        except ContainerError as e:
            print(f"Error: Failed to start container '{self.name}': {e}")
        except APIError as e:
            print(f"API error while starting container '{self.name}': {e}")
        except DockerException as e:
            print(f"Unexpected Docker error while starting container '{self.name}': {e}")

    def on_started(self):
        pass

    def stop(self):
        self.container.stop()

    def restart(self):
        try:
            self.container.restart()

        except ImageNotFound as e:
            print(f"Error: Failed to restart container '{self.name}': {e}")

    def status(self) -> EnvStatus:
        docker_status = self.container.status
        return EnvStatus(docker_status) if docker_status in EnvStatus._value2member_map_ else EnvStatus.UNKNOWN

    def get_access_info(self) -> dict:
        pass

    def destroy(self):
        self.container.stop()
        self.container.remove()

        # TODO free occupied ports

class VMEnvironment(Environment):
    def __init__(
            self,
            name: str,
            exposed_ports: list,
            host_ports: list,
            args: dict
    ):
        super().__init__(name, exposed_ports, host_ports, args)

    def start(self):
        pass

    def on_started(self):
        pass

    def stop(self):
        pass

    def restart(self):
        pass

    def status(self) -> str:
        pass

    def get_access_info(self) -> dict:
        pass

    def destroy(self):
        pass


if __name__ == "__main__":
    env = DockerEnvironment(
        name="test-env",
        image="docker-test-image",
        exposed_ports=[5000],
        host_ports=[8080],
        args={"FLAG": "TEST123"}
    )

    env.start()
    print(f"Status: {env.status()}")
    print(f"Access info: {env.get_access_info()}")

    input("Naciśnij Enter aby zatrzymać kontener...")
    env.stop()