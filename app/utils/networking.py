import shlex
import docker
from docker.client import DockerClient
from docker.models.networks import Network
from flask import current_app
import subprocess
import logging

MAX_NETWORKS = 62976


def get_cluster_subnet(cluster_id: int) -> str:
    if cluster_id < 1:
        raise ValueError("cluster_id must be an integer greater than 0")

    x = (cluster_id - 1) // 256 + 10
    y = (cluster_id - 1) % 256

    return f"10.{x}.{y}.0/24"


def get_host_ip_address(cluster_id: int, host_id: int) -> str:
    if cluster_id < 1:
        raise ValueError("cluster_id must be an integer greater than 0")
    if not (0 <= host_id <= 255):
        raise ValueError("host_id must be in range 0–255")

    x = (cluster_id - 1) // 256 + 10
    y = (cluster_id - 1) % 256

    return f"10.{x}.{y}.{host_id}"


def get_gateway_ip(cluster_id: int) -> str:
    subnet = get_cluster_subnet(cluster_id)
    return subnet.replace('.0/24', '.1')


def get_bridge_name(cluster_id: int) -> str:
    if cluster_id < 1:
        raise ValueError("cluster_id must be an integer greater than 0")

    return f'venvbr{cluster_id}'


def create_docker_network(docker_client: DockerClient, network_name: str, bridge_name, cluster_id: int) -> Network:
    subnet = get_cluster_subnet(cluster_id)
    gateway = get_gateway_ip(cluster_id)

    try:
        return docker_client.networks.create(
            name=network_name,
            driver="macvlan",
            options={
                "parent": bridge_name
            },
            ipam=docker.types.IPAMConfig(
                pool_configs=[
                    docker.types.IPAMPool(
                        subnet=subnet,
                        gateway=gateway,
                    )
                ]
            )
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


def forward_port(vm_ip: str, vm_port: int, host_port: int, debug=False) -> subprocess.Popen:
    try:
        cmd = f"socat TCP-LISTEN:{host_port},fork TCP:{vm_ip}:{vm_port}"
        logging.debug(f"Starting socat: {cmd}")

        if debug:
            proc: subprocess.Popen[bytes] = subprocess.Popen(shlex.split(cmd))
        else:
            proc: subprocess.Popen[bytes] = subprocess.Popen(
                shlex.split(cmd),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        return proc

    except Exception as e:
        logging.error(f"Failed to start socat forwarding: {e}")
        raise RuntimeError(f"socat failed: {e}")

