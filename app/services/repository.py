from __future__ import annotations
from typing import Iterable, Optional, Sequence

from app.extensions import db
from app.models import Cluster, Environment, ClusterEnvironment


class ClusterRepository:
    def get_by_id(self, cluster_id: int) -> Optional[Cluster]:
        return Cluster.query.get(cluster_id)

    def get_by_name(self, name: str) -> Optional[Cluster]:
        return Cluster.query.filter_by(name=name).first()

    def add(self, cluster: Cluster) -> None:
        db.session.add(cluster)

    def delete(self, cluster: Cluster) -> None:
        db.session.delete(cluster)


class EnvironmentRepository:
    def get_by_id(self, env_id: int) -> Optional[Environment]:
        return Environment.query.get(env_id)

    def list_all_for_creator(self) -> Sequence[Environment]:
        return (
            Environment.query.outerjoin(Environment.docker)
            .outerjoin(Environment.vm)
            .order_by(Environment.name.asc())
            .all()
        )

    def get_by_ids(self, ids: Iterable[int]) -> list[Environment]:
        ids = list(ids)
        if not ids:
            return []
        return Environment.query.filter(Environment.id.in_(ids)).all()

    def add(self, env: Environment) -> None:
        db.session.add(env)

    def delete(self, env: Environment) -> None:
        db.session.delete(env)


class ClusterEnvironmentRepository:
    def add_links(self, cluster_id: int, env_ids: Iterable[int]) -> None:
        links = [
            ClusterEnvironment(cluster_id=cluster_id, environment_id=eid)
            for eid in env_ids
        ]
        if links:
            db.session.add_all(links)
