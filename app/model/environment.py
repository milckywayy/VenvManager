from abc import ABC, abstractmethod
from datetime import datetime
from flask import current_app


class Environment(ABC):
    def __init__(self, name: str, exposed_ports: list, host_ports: list, args: dict):
        # TODO add network parsing
        self.name = name

        if len(host_ports) == 0 or len(host_ports) != len(exposed_ports):
            raise ValueError("Ports and exposed ports must have same length.")

        self.host_ports = host_ports
        self.exposed_ports = exposed_ports
        self.args = args

        self.creation_time = datetime.now()

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def on_started(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def restart(self):
        pass

    @abstractmethod
    def status(self):
        pass

    @abstractmethod
    def get_access_info(self):
        pass

    @abstractmethod
    def destroy(self):
        pass

    def get_time_left(self):
        now = datetime.now()
        elapsed = (now - self.creation_time).total_seconds()
        remaining = current_app.config.get('ENV_TTL') - elapsed
        return max(0, int(remaining))

    def is_expired(self):
        return self.get_time_left() <= 0
