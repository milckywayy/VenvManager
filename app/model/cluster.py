from app.model.environment import Environment

class Cluster:
    def __init__(self, name):
        self.name = name
        self.environments = []

    def add_environment(self, env: Environment):
        self.environments.append(env)

    def start_all(self):
        for env in self.environments:
            env.start()

    def stop_all(self):
        for env in self.environments:
            env.stop()

    def status_all(self) -> dict:
        return {env.name: env.status() for env in self.environments}

    def get_all_access_info(self) -> dict:
        return {env.name: env.get_access_info() for env in self.environments}
