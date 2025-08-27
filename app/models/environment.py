from app.extensions import db
from sqlalchemy.orm import validates


class Cluster(db.Model):
    __tablename__ = "clusters"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True, index=True)

    environment_links = db.relationship(
        "ClusterEnvironment",
        back_populates="cluster",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    environments = db.relationship(
        "Environment",
        secondary="cluster_environments",
        back_populates="clusters",
        viewonly=True,
    )

    def __repr__(self):
        return f"<Cluster id={self.id} name={self.name!r}>"


class Environment(db.Model):
    __tablename__ = "environments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    ports = db.Column(db.JSON, nullable=True, default=list)
    access_info = db.Column(db.String(256), nullable=True, default=list)

    cluster_links = db.relationship(
        "ClusterEnvironment",
        back_populates="environment",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    clusters = db.relationship(
        "Cluster",
        secondary="cluster_environments",
        back_populates="environments",
        viewonly=True,
    )

    docker = db.relationship(
        "DockerEnvironment",
        back_populates="environment",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    vm = db.relationship(
        "VMEnvironment",
        back_populates="environment",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @validates("ports")
    def _validate_ports(self, key, value):
        if value is None:
            return []
        if not isinstance(value, (list, tuple)):
            raise ValueError("ports must be a list of integers")
        cleaned = []
        for p in value:
            if not isinstance(p, int):
                raise ValueError("each port must be an integer")
            if not (1 <= p <= 65535):
                raise ValueError(f"invalid port number: {p}")
            cleaned.append(p)
        return cleaned


class ClusterEnvironment(db.Model):
    __tablename__ = "cluster_environments"

    id = db.Column(db.Integer, primary_key=True)
    cluster_id = db.Column(
        db.Integer,
        db.ForeignKey("clusters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    environment_id = db.Column(
        db.Integer,
        db.ForeignKey("environments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    cluster = db.relationship("Cluster", back_populates="environment_links")
    environment = db.relationship("Environment", back_populates="cluster_links")

    def __repr__(self):
        return f"<ClusterEnvironment id={self.id} cluster_id={self.cluster_id} environment_id={self.environment_id} alias={self.alias!r}>"


class DockerEnvironment(db.Model):
    __tablename__ = "docker_environments"

    id = db.Column(
        db.Integer,
        db.ForeignKey("environments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    image = db.Column(db.String(255), nullable=False, index=True)

    environment = db.relationship("Environment", back_populates="docker")


class VMEnvironment(db.Model):
    __tablename__ = "vm_environments"

    id = db.Column(
        db.Integer,
        db.ForeignKey("environments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    template = db.Column(db.JSON, nullable=False)
    base_image_path = db.Column(db.String(512), nullable=False)

    environment = db.relationship("Environment", back_populates="vm")
