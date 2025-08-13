set shell := ["bash", "-c"]
export COMPOSE_FILE := "docker-compose.dev.yml"
export FLASK_ENV := "development"


default:
    @just --list

check-env:
    python3 app/load_env.py

run:
    #!/usr/bin/env bash
    set -euo pipefail
    trap 'docker compose -f {{COMPOSE_FILE}} down' EXIT
    docker compose up -d --remove-orphans
    python3 run.py

prune:
    @docker compose down -v

db +args:
    @docker compose up -d --remove-orphans
    flask db {{args}}
    @docker compose down
