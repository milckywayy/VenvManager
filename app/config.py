from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=".env")
env_file = f".env.{os.getenv('FLASK_ENV', 'development')}"
load_dotenv(dotenv_path=env_file, override=True)


class Config:
    MAX_NETWORKS = 65536
