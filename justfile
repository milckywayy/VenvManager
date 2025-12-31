set shell := ["bash", "-c"]
export COMPOSE_FILE := "docker-compose.dev.yml"
export FLASK_ENV := "development"
export LOG_DIR := "./.logs"


default:
    @just --list

check-env:
    python3 app/load_env.py

up-db:
    docker compose up -d --remove-orphans

up-admin: up-db
    mkdir -p {{LOG_DIR}}
    -screen -S vm_manager_admin_dev -X quit
    screen -dmS vm_manager_admin_dev bash -lc '\
        set -o pipefail; \
        APP_MODE=admin exec python3 -u run.py 2>&1 | tee -a {{LOG_DIR}}/admin.log \
    '
    @echo "Admin application started (logs: {{LOG_DIR}}/admin.log)"

up-api: up-db
    mkdir -p {{LOG_DIR}}
    -screen -S vm_manager_api_dev -X quit
    screen -dmS vm_manager_api_dev bash -lc '\
        set -o pipefail; \
        APP_MODE=api exec python3 -u run.py 2>&1 | tee -a {{LOG_DIR}}/api.log \
    '
    @echo "API application started (logs: {{LOG_DIR}}/api.log)"

up: up-admin up-api
    @echo "Application started"

down:
    -screen -S vm_manager_admin_dev -X quit
    -screen -S vm_manager_api_dev -X quit
    docker compose down
    @echo "Application and containers have been stopped"

logs:
    tail -n 200 -f {{LOG_DIR}}/api.log

logs-admin:
    tail -n 200 -f {{LOG_DIR}}/admin.log

prune:
    docker compose down -v

db +args:
    docker compose up -d --remove-orphans
    flask db {{args}}
    docker compose down
