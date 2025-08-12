check-env FLASK_ENV:
    FLASK_ENV={{FLASK_ENV}} python3 app/load_env.py

dev:
    #!/usr/bin/env bash
    set -Eeuo pipefail
    trap 'docker compose -f docker-compose.dev.yml down' EXIT

    docker compose -f docker-compose.dev.yml up -d

    FLASK_ENV=development python3 run.py

prod:
    #!/usr/bin/env bash
    set -Eeuo pipefail
    trap 'docker compose -f docker-compose.prod.yml down' EXIT

    docker compose -f docker-compose.prod.yml up -d

    FLASK_ENV=production gunicorn "app:create_app()" --bind 0.0.0.0:8000 --workers 4


prune:
    docker compose -f docker-compose.dev.yml down -v
    docker compose -f docker-compose.prod.yml down -v
