import os
from pathlib import Path
from dotenv import load_dotenv

REQUIRED_ENV_VARS = [
    "PYTHON_ENV",
    "DEBUG",
    "SECRET_KEY",
    "HOST_API",
    "PORT_API",
    "API_BASE_URL",
    "HOST_ADMIN",
    "PORT_ADMIN",
    "LIBVIRT_CLIENT",
    "VM_DEFAULT_BRIDGE",
    "ENV_BOOT_POLL_INTERVAL",
    "VM_BOOT_TIMEOUT",
    "CLUSTER_TTL_SECONDS",
    "CLUSTER_TTL_ALLOW_EXTEND_TIME_SECONDS",
    "CLUSTER_TTL_EXTEND_SECONDS",
    "CLUSTER_TTL_POLL_SECONDS",
]

REQUIRED_DIR_PATHS = [
    "VM_OVERLAYS_PATH",
    "VM_TEMPLATES_PATH",
    "VM_BASE_IMAGES_PATH",
]

REQUIRED_FILE_PATHS = [
    "LOG_FILE_PATH",
]


def load_env(path_prefix=""):
    env_file = os.getenv("FLASK_ENV", "development")
    env_path = f"{path_prefix}.env.{env_file}"

    load_dotenv(f"{path_prefix}.env", override=False)
    load_dotenv(env_path, override=True)

    validate()


def validate():
    missing_vars = []
    missing_dirs = []
    missing_file_dirs = []

    for var in REQUIRED_ENV_VARS + REQUIRED_DIR_PATHS + REQUIRED_FILE_PATHS:
        if os.getenv(var) is None:
            missing_vars.append(var)

    for var in REQUIRED_DIR_PATHS:
        value = os.getenv(var)
        if value:
            path = Path(value)
            if not path.is_dir():
                missing_dirs.append(str(path))

    for var in REQUIRED_FILE_PATHS:
        value = os.getenv(var)
        if value:
            file_path = Path(value)
            parent_dir = file_path.parent
            if not parent_dir.is_dir():
                missing_file_dirs.append(str(parent_dir))

    error_messages = []
    if missing_vars:
        error_messages.append(
            "Missing environment variables: " + ", ".join(missing_vars)
        )
    if missing_dirs:
        error_messages.append("Missing directories: " + ", ".join(missing_dirs))
    if missing_file_dirs:
        error_messages.append(
            "Missing directories for file paths: " + ", ".join(missing_file_dirs)
        )

    if error_messages:
        raise EnvironmentError("\n".join(error_messages))


if __name__ == "__main__":
    try:
        load_env()

    except EnvironmentError as e:
        print(e)

    print("Successfully validated environment")
