from app.utils.networking import create_docker_network, remove_docker_network
from environment import Environment
from app.model.status import EnvStatus
import docker
from docker.errors import ImageNotFound, APIError, DockerException, ContainerError
from docker.models.networks import Network

docker_client = docker.from_env()


class DockerEnvironment(Environment):
    def __init__(
            self,
            name: str,
            image: str,
            index: int,
            internal_ports: list,
            published_ports: list,
            network: Network,
            args: dict
    ):
        super().__init__(name, internal_ports, published_ports, args)
        self.image = image
        self.network = network
        self.index = index

        self.container = None

    def start(self):
        try:
            self.container = docker_client.containers.run(
                self.image,
                detach=True,
                ports={f'{internal}/tcp': published for internal, published in
                       zip(self.internal_ports, self.published_ports)},
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
        self.network.connect(self.container.id, ipv4_address=f"10.10.10.{str(self.index + 10)}")

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
    bridge_name = 'venvbr0'
    network_name = 'docker-test'
    docker_network = create_docker_network(docker_client, network_name, bridge_name)
    print(docker_network)

    container1 = DockerEnvironment(
        name="test1",
        image="test",
        index=0,
        internal_ports=[80],
        published_ports=[5000],
        network=docker_network,
        args={"FLAG": "TEST123"}
    )

    container2 = DockerEnvironment(
        name="test2",
        image="ubuntu-ssh",
        index=1,
        internal_ports=[22],
        published_ports=[5001],
        network=docker_network,
        args={"FLAG": "TEST123"}
    )
    print(container2)

    container1.start()
    container1.on_started()

    container2.start()
    container2.on_started()

    input("Naciśnij Enter aby usunąć kontener...")

    container1.destroy()
    container2.destroy()

    remove_docker_network(docker_network)