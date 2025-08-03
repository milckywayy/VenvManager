from enum import Enum

class EnvStatus(Enum):
    CREATED = "created"
    BOOTING = "booting"
    RUNNING = "running"
    RESTARTING = "restarting"
    PAUSED = "paused"
    UNKNOWN = "unknown"
