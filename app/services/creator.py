from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    Cluster,
    Environment,
    DockerEnvironment as DockerEnvModel,
    VMEnvironment as VMEnvModel,
)
from app.services.repository import (
    ClusterRepository,
    EnvironmentRepository,
    ClusterEnvironmentRepository,
)


class ValidationError(RuntimeError):
    pass


class NotFoundError(RuntimeError):
    pass


class AlreadyExistsError(RuntimeError):
    pass


@dataclass(frozen=True)
class CreateDockerEnvCmd:
    name: str
    image: str
    ports: list[int]
    access_info: str


@dataclass(frozen=True)
class CreateVMEnvCmd:
    name: str
    template: str
    base_image_path: str
    ports: list[int]
    access_info: str


@dataclass(frozen=True)
class CreateClusterCmd:
    name: str
    environment_ids: list[int]


class CreatorService:
    def __init__(
        self,
        *,
        clusters: ClusterRepository,
        envs: EnvironmentRepository,
        links: ClusterEnvironmentRepository,
    ):
        self.clusters = clusters
        self.envs = envs
        self.links = links

    def create_docker_env(self, cmd: CreateDockerEnvCmd) -> Environment:
        name = (cmd.name or "").strip()
        if not name:
            raise ValidationError("Environment name is required.")
        if not cmd.image:
            raise ValidationError("Docker image is required.")

        env = Environment(
            name=name.replace(" ", "-"),
            ports=list(cmd.ports or []),
            access_info=cmd.access_info,
        )
        env.docker = DockerEnvModel(image=cmd.image)

        try:
            self.envs.add(env)
            db.session.commit()
            return env
        except Exception:
            db.session.rollback()
            raise

    def create_vm_env(self, cmd: CreateVMEnvCmd) -> Environment:
        name = (cmd.name or "").strip()
        if not name:
            raise ValidationError("Environment name is required.")
        if not cmd.template:
            raise ValidationError("VM template is required.")
        if not cmd.base_image_path:
            raise ValidationError("Base image path is required.")

        env = Environment(
            name=name.replace(" ", "-"),
            ports=list(cmd.ports or []),
            access_info=cmd.access_info,
        )
        env.vm = VMEnvModel(template=cmd.template, base_image_path=cmd.base_image_path)

        try:
            self.envs.add(env)
            db.session.commit()
            return env
        except Exception:
            db.session.rollback()
            raise

    def create_cluster_with_envs(self, cmd: CreateClusterCmd) -> Cluster:
        name = (cmd.name or "").strip()
        if not name:
            raise ValidationError("Cluster name is required.")
        if self.clusters.get_by_name(name):
            raise AlreadyExistsError(f"Cluster named '{name}' already exists.")

        cluster = Cluster(name=name)
        try:
            self.clusters.add(cluster)
            db.session.flush()

            env_ids = list(cmd.environment_ids or [])
            if env_ids:
                envs = self.envs.get_by_ids(env_ids)
                found_ids = {e.id for e in envs}
                missing = [eid for eid in env_ids if eid not in found_ids]
                if missing:
                    raise ValidationError(f"Unknown environment ids: {missing}")

                self.links.add_links(cluster_id=cluster.id, env_ids=found_ids)

            db.session.commit()
            return cluster
        except Exception:
            db.session.rollback()
            raise

    def delete_environment(self, env_id: int) -> None:
        env = self.envs.get_by_id(env_id)
        if not env:
            raise NotFoundError("Environment not found")

        try:
            self.envs.delete(env)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            raise IntegrityError(str(e), params=None, orig=e.orig)

    def delete_cluster(self, cluster_id: int) -> None:
        cluster = self.clusters.get_by_id(cluster_id)
        if not cluster:
            raise NotFoundError("Cluster not found")

        try:
            self.clusters.delete(cluster)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            raise IntegrityError(str(e), params=None, orig=e.orig)
