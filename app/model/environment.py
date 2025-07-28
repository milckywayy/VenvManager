from abc import ABC, abstractmethod


class Environment(ABC):
    def __init__(self, name):
        self.name = name

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def status(self):
        pass

    @abstractmethod
    def get_access_info(self):
        pass


class DockerEnvironment(Environment):
    def __init__(self, name):
        super().__init__(name)

    def start(self):
        pass

    def stop(self):
        pass

    def status(self) -> str:
        pass

    def get_access_info(self) -> dict:
        pass


class VMEnvironment(Environment):
    def __init__(self, name: str):
        super().__init__(name)

    def start(self):
        pass

    def stop(self):
        pass

    def status(self) -> str:
        pass

    def get_access_info(self) -> dict:
        pass
