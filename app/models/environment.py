from app import db
from sqlalchemy.orm import validates


class Cluster(db.Model):
    __tablename__ = "clusters"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True, index=True)

    environments = db.relationship(
        "Environment",
        back_populates="cluster",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"<Cluster id={self.id} name={self.name!r}>"


class Environment(db.Model):
    __tablename__ = "environments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    ports = db.Column(db.JSON, nullable=True, default=list)

    cluster_id = db.Column(
        db.Integer,
        db.ForeignKey("clusters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cluster = db.relationship("Cluster", back_populates="environments")

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
            raise ValueError("ports must be a list of {internal, published} objects")
        cleaned = []
        for p in value:
            if not isinstance(p, dict):
                raise ValueError(
                    "each port entry must be a dict with 'internal' and 'published'"
                )
            internal = p.get("internal")
            published = p.get("published")
            if not (isinstance(internal, int) and isinstance(published, int)):
                raise ValueError("ports must be integers")
            if not (1 <= internal <= 65535 and 1 <= published <= 65535):
                raise ValueError(f"invalid port mapping: {p}")
            cleaned.append({"internal": internal, "published": published})
        return cleaned


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
    template_path = db.Column(db.String(512), nullable=False)
    base_image_path = db.Column(db.String(512), nullable=False)

    environment = db.relationship("Environment", back_populates="vm")
