import os
from pathlib import Path


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(24))
    OVERLAY_PATH = Path('/var/lib/libvirt/images/')

    DEBUG = False
    ENV_TTL = None

class DevelopmentConfig(Config):
    DEBUG = True
    ENV_TTL = 3600

class ProductionConfig(Config):
    DEBUG = False
    ENV_TTL = 1800

config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig
}
