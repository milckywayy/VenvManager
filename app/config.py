import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(24))
    DEBUG = False
    ENV_TTL = 1800

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
