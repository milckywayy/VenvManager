from abc import ABC, abstractmethod

from app.models.status import EnvStatus


class Environment(ABC):
    def __init__(
        self, name: str, display_name: str, internal_ports: list, published_ports: list
    ):
        self.name = name
        self.display_name = display_name

        if len(internal_ports) == 0 or len(internal_ports) != len(published_ports):
            raise ValueError("Ports and exposed ports must have same length.")

        self.internal_ports = internal_ports
        self.published_ports = published_ports

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def restart(self):
        pass

    @abstractmethod
    def status(self) -> EnvStatus:
        pass

    @abstractmethod
    def get_access_info(self):
        pass

    @abstractmethod
    def destroy(self):
        pass
