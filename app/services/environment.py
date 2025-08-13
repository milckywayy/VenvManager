from app.extensions import db
from app.models import Cluster, Environment, DockerEnvironment, VMEnvironment


def create_cluster(name: str) -> Cluster:
    cluster = Cluster(name=name)
    db.session.add(cluster)
    db.session.commit()

    return cluster


def create_docker_env(name: str, image: str, ports: list[dict]) -> Environment:
    env = Environment(cluster_id=None, name=name, ports=ports)
    env.docker = DockerEnvironment(image=image)
    db.session.add(env)
    db.session.commit()
    return env


def create_vm_env(name: str, template_path: str, base_image_path: str) -> Environment:
    env = Environment(name=name)
    env.vm = VMEnvironment(template_path=template_path, base_image_path=base_image_path)
    db.session.add(env)
    db.session.commit()
    return env


def destroy_env(env_id: int) -> None:
    env = Environment.query.get_or_404(env_id)
    db.session.delete(env)
    db.session.commit()
