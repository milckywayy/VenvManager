import os
from app import create_app_api, create_app_admin

mode = os.getenv("APP_MODE", "admin")

if mode == "api":
    app = create_app_api()
    host = os.environ.get("HOST_API", "localhost")
    port = int(os.environ.get("PORT_API", 8080))
elif mode == "admin":
    app = create_app_admin()
    host = os.environ.get("HOST_ADMIN", "localhost")
    port = int(os.environ.get("PORT_ADMIN", 8080))
else:
    raise RuntimeError(f"Unknown APP_MODE: {mode}")

if __name__ == "__main__":
    app.run(host=host, port=port, debug=bool(int(os.environ.get("DEBUG", True))))
