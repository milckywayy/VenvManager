from abc import ABC, abstractmethod
from typing import Dict

from app.models.status import EnvStatus


class Environment(ABC):
    def __init__(
        self,
        name: str,
        display_name: str,
        internal_ports: list,
        published_ports: list,
        access_info: str,
    ):
        self.name = name
        self.display_name = display_name

        if len(internal_ports) == 0 or len(internal_ports) != len(published_ports):
            raise ValueError("Ports and exposed ports must have same length.")

        self.ip = None
        self.internal_ports = internal_ports
        self.published_ports = published_ports

        self.access_info = access_info

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def restart(self):
        pass

    @abstractmethod
    def status(self) -> EnvStatus:
        pass

    def get_access_info(self):
        result = self.access_info
        result = result.replace("{{ip}}", self.ip or "unknown")
        for internal, published in zip(self.internal_ports, self.published_ports):
            result = result.replace(f"{{{{{internal}}}}}", str(published))
        return {"ip": self.ip, "access": result}

    @abstractmethod
    def get_resource_usage(self) -> Dict[str, float]:
        pass

    @abstractmethod
    def destroy(self):
        pass
