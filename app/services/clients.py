import os
import docker
import libvirt


def create_docker_client():
    return docker.from_env()


def create_libvirt_client():
    return libvirt.open(os.getenv("LIBVIRT_CLIENT"))
