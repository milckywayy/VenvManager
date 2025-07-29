from enum import Enum

class EnvStatus(Enum):
    CREATED = "created"
    RUNNING = "running"
    RESTARTING = "restarting"
    PAUSED = "paused"
    UNKNOWN = "unknown"
