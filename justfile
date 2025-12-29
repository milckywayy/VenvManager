set shell := ["bash", "-c"]
export COMPOSE_FILE := "docker-compose.dev.yml"
export FLASK_ENV := "development"


default:
    @just --list

check-env:
    python3 app/load_env.py

up:
    -screen -S vm_manager_dev -X quit
    docker compose up -d --remove-orphans
    screen -dmS vm_manager_dev bash -c 'exec python3 run.py'

    @echo "Application started"

down:
    -screen -S vm_manager_dev -X quit
    docker compose down
    @echo "Application and containers have been stopped"

logs:
    screen -S vm_manager_dev -X hardcopy -h /tmp/dev_app.log
    cat /tmp/dev_app.log

prune:
    docker compose down -v

db +args:
    docker compose up -d --remove-orphans
    flask db {{args}}
    docker compose down
