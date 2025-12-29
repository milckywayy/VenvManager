import threading
from typing import Dict, Optional

from app.runtime import Cluster


class ClusterRegistry:
    def __init__(self):
        self._lock = threading.Lock()
        self._clusters: Dict[str, Cluster] = {}

    def get(self, session_id: str) -> Optional[Cluster]:
        with self._lock:
            return self._clusters.get(session_id)

    def set(self, session_id: str, cluster: Cluster) -> None:
        with self._lock:
            self._clusters[session_id] = cluster

    def pop(self, session_id: str) -> Optional[Cluster]:
        with self._lock:
            return self._clusters.pop(session_id, None)

    def items(self):
        with self._lock:
            return list(self._clusters.items())
