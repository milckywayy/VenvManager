from environment import Environment
from app.model.status import EnvStatus
import docker
from docker.errors import ImageNotFound, APIError, DockerException, ContainerError

docker_client = docker.from_env()


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
            self.container = docker_client.containers.run(
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
        return {}

    def destroy(self):
        self.container.stop()
        self.container.remove()

        # TODO free occupied ports


if __name__ == "__main__":
    env = DockerEnvironment(
        name="test",
        image="test",
        exposed_ports=[5000],
        host_ports=[80],
        args={"FLAG": "TEST123"}
    )

    env.start()
    print(f"Status: {env.status()}")
    print(f"Access info: {env.get_access_info()}")

    input("Naciśnij Enter aby zatrzymać kontener...")
    env.destroy()