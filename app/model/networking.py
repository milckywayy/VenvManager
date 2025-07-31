import docker
from docker.client import DockerClient
from docker.models.networks import Network


def create_docker_network(docker_client: DockerClient, network_name: str, bridge_name) -> Network:
    try:
        return docker_client.networks.create(
            network_name,
            driver='bridge',
            ipam=docker.types.IPAMConfig(
                pool_configs=[docker.types.IPAMPool(
                    subnet='10.10.10.0/24',
                    gateway='10.10.10.1'
                )]
            ),
            options={'com.docker.network.bridge.name': bridge_name}
        )
    except docker.errors.APIError as e:
        print(f"Network creation failed (maybe it exists?): {e}")
        try:
            return docker_client.networks.get(network_name)
        except docker.errors.NotFound:
            return None


def remove_docker_network(network: Network) -> bool:
    name = network.name

    try:
        network.remove()
        print(f"Network '{name}' removed successfully.")
        return True

    except docker.errors.APIError as e:
        print(f"Failed to remove network '{name}': {e}")
        return False


if __name__ == "__main__":
    client = docker.from_env()
    network = create_docker_network(client, 'test-net')

    if network:
        input(f"Network ready: {network.name}")
        remove_docker_network(network)
    else:
        print("Network creation failed.")
