import threading
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta

from app.runtime import Cluster

ClusterEntry = Tuple[Cluster, datetime, datetime]


class ClusterRegistry:
    def __init__(self):
        self._lock = threading.Lock()
        self._clusters: Dict[str, ClusterEntry] = {}

    def get(self, session_id: str) -> Optional[Cluster]:
        with self._lock:
            entry = self._clusters.get(session_id)
            return entry[0] if entry else None

    def get_entry(self, session_id: str) -> Optional[ClusterEntry]:
        with self._lock:
            return self._clusters.get(session_id)

    def set(self, session_id: str, cluster: Cluster, ttl_seconds: int) -> None:
        now = datetime.now()
        expires_at = now + timedelta(seconds=ttl_seconds)
        with self._lock:
            self._clusters[session_id] = (cluster, now, expires_at)

    def extend_ttl(self, session_id: str, seconds: int) -> None:
        if seconds <= 0:
            return
        with self._lock:
            entry = self._clusters.get(session_id)
            if not entry:
                return
            cluster, created_at, expires_at = entry
            self._clusters[session_id] = (
                cluster,
                datetime.now(),
                expires_at + timedelta(seconds=seconds),
            )

    def expired_sessions(self):
        now = datetime.now()
        with self._lock:
            return [
                session_id
                for session_id, (_, _, expires_at) in self._clusters.items()
                if expires_at <= now
            ]

    def pop(self, session_id: str) -> Optional[Cluster]:
        with self._lock:
            entry = self._clusters.pop(session_id, None)
            return entry[0] if entry else None

    def items(self):
        with self._lock:
            return list(self._clusters.items())
