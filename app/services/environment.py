from app.extensions import db
from app.models import Cluster, Environment, DockerEnvironment, VMEnvironment


def create_cluster(name: str) -> Cluster:
    cluster = Cluster(name=name)
    db.session.add(cluster)
    db.session.commit()

    return cluster


def create_docker_env(name: str, image: str, ports: list[dict]) -> Environment:
    env = Environment(name=name, ports=ports)
    env.docker = DockerEnvironment(image=image)
    db.session.add(env)
    db.session.commit()
    return env


def create_vm_env(
    name: str, template: str, base_image_path: str, ports: list[dict]
) -> Environment:
    env = Environment(name=name, ports=ports)
    env.vm = VMEnvironment(template=template, base_image_path=base_image_path)
    db.session.add(env)
    db.session.commit()
    return env
