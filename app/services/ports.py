import random
import threading
from dataclasses import dataclass
from typing import Iterable, List


class NoAvailablePortsError(RuntimeError):
    pass


@dataclass
class PortsConfig:
    begin: int
    end: int


class PortPool:
    def __init__(self, ports: Iterable[int]):
        self._lock = threading.Lock()
        self._available = list(ports)

    def allocate_many(self, count: int) -> List[int]:
        with self._lock:
            if len(self._available) < count:
                raise NoAvailablePortsError("No available ports")
            chosen = random.sample(self._available, k=count)
            for p in chosen:
                self._available.remove(p)
            return chosen

    def release_many(self, ports: Iterable[int]) -> None:
        with self._lock:
            for p in ports:
                if p not in self._available:
                    self._available.append(p)
