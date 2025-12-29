set shell := ["bash", "-c"]
export COMPOSE_FILE := "docker-compose.dev.yml"
export FLASK_ENV := "development"


default:
    @just --list

check-env:
    python3 app/load_env.py

up-db:
    docker compose up -d --remove-orphans

up-admin: up-db
    -screen -S vm_manager_admin_dev -X quit
    screen -dmS vm_manager_admin_dev bash -c 'APP_MODE=admin exec python3 run.py'
    @echo "Admin application started"

up-api: up-db
    -screen -S vm_manager_api_dev -X quit
    screen -dmS vm_manager_api_dev bash -c 'APP_MODE=api exec python3 run.py'
    @echo "API application started"


up: up-admin up-api
    @echo "Application started"

down:
    -screen -S vm_manager_admin_dev -X quit
    -screen -S vm_manager_api_dev -X quit
    docker compose down
    @echo "Application and containers have been stopped"

logs:
    screen -S vm_manager_api_dev -X hardcopy -h /tmp/vm_manager_api_dev.log
    cat /tmp/dev_app.log

logs-admin:
    screen -S vm_manager_admin_dev -X hardcopy -h /tmp/vm_manager_admin_dev.log
    cat /tmp/dev_app.log

prune:
    docker compose down -v

db +args:
    docker compose up -d --remove-orphans
    flask db {{args}}
    docker compose down
