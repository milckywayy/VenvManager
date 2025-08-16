import shlex
from docker.client import DockerClient
from docker.models.networks import Network
from docker.types import IPAMConfig, IPAMPool
from docker.errors import APIError, NotFound
import subprocess
import logging
from typing import Optional

from app.config import Config

MAX_NETWORKS = Config.MAX_NETWORKS

IFACE_XML = """
<network>
  <name>{network_name}</name>
  <forward mode="nat"/>
  <bridge name="{network_name}" stp="on" delay="0"/>
  <ip address="{gateway_ip}" netmask="255.255.255.0">
    <dhcp>
      <range start="{start_ip}" end="{end_ip}"/>
    </dhcp>
  </ip>
</network>
"""


NETWORK_TEMPLATE = "10.{x}.{y}.{host}"


def get_cluster_subnet(cluster_id: int) -> str:
    if cluster_id < 0:
        raise ValueError("cluster_id must be an integer >= 0")

    x = cluster_id // 256
    y = cluster_id % 256
    return NETWORK_TEMPLATE.format(x=x, y=y, host=0)


def get_cluster_cidr(cluster_id: int) -> str:
    if cluster_id < 0:
        raise ValueError("cluster_id must be an integer >= 0")
    return f"{get_cluster_subnet(cluster_id)}/24"


def get_host_ip_address(cluster_id: int, host_id: int) -> str:
    if cluster_id < 0:
        raise ValueError("cluster_id must be an integer >= 0")
    if not (2 <= host_id <= 254):
        raise ValueError("host_id must be in range 2–254")

    x = cluster_id // 256
    y = cluster_id % 256
    return NETWORK_TEMPLATE.format(x=x, y=y, host=host_id)


def get_gateway_ip(cluster_id: int) -> str:
    if cluster_id < 0:
        raise ValueError("cluster_id must be an integer >= 0")

    x = cluster_id // 256
    y = cluster_id % 256
    return NETWORK_TEMPLATE.format(x=x, y=y, host=1)


def _get_docker_network_name(bridge_name: str) -> str:
    return f"{bridge_name}-docker"


def create_network(network_name: str, cluster_id: int) -> str:
    network_xml = IFACE_XML.format(
        network_name=network_name,
        gateway_ip=get_gateway_ip(cluster_id),
        start_ip=get_host_ip_address(cluster_id, 100),
        end_ip=get_host_ip_address(cluster_id, 200),
    )
    define_cmd = ["virsh", "net-define", "/dev/stdin"]
    subprocess.run(define_cmd, input=network_xml.encode(), check=True)

    subprocess.run(["virsh", "net-start", network_name], check=True)
    subprocess.run(["virsh", "net-autostart", network_name], check=True)

    return network_name


def remove_network(network_name: str):
    subprocess.run(["virsh", "net-destroy", network_name], check=False)
    subprocess.run(["virsh", "net-undefine", network_name], check=False)


def create_docker_network(
    docker_client: DockerClient, bridge_name: str, cluster_id: int
) -> Optional[Network]:
    subnet_cidr = get_cluster_cidr(cluster_id)
    docker_network_name = _get_docker_network_name(bridge_name)

    try:
        return docker_client.networks.create(
            name=docker_network_name,
            driver="bridge",
            options={"com.docker.network.bridge.name": bridge_name},
            ipam=IPAMConfig(pool_configs=[IPAMPool(subnet=subnet_cidr)]),
        )

    except APIError as e:
        logging.exception(f"Network creation failed (maybe it exists?): {e}")
        try:
            return docker_client.networks.get(docker_network_name)
        except NotFound:
            return None


def remove_docker_network(docker_network: Optional[Network]) -> bool:
    if docker_network is None:
        return False

    try:
        docker_network.remove()
        return True
    except APIError:
        return False


def forward_port(
    vm_ip: str, vm_port: int, host_port: int, debug: bool = False
) -> subprocess.Popen:
    try:
        cmd = f"socat TCP-LISTEN:{host_port},fork,reuseaddr TCP:{vm_ip}:{vm_port}"
        logging.debug(f"Starting socat: {cmd}")

        if debug:
            proc: subprocess.Popen = subprocess.Popen(shlex.split(cmd))
        else:
            proc: subprocess.Popen = subprocess.Popen(
                shlex.split(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        return proc

    except Exception as e:
        logging.error(f"Failed to start socat forwarding: {e}")
        raise RuntimeError(f"socat failed: {e}")
