check-env FLASK_ENV:
    FLASK_ENV={{FLASK_ENV}} python3 app/load_env.py

dev:
    FLASK_ENV=development python3 run.py

prod:
    FLASK_ENV=production gunicorn "app:create_app()" --bind 0.0.0.0:8000 --workers 4

make-bridge *args:
    ./app/scripts/setup_bridge {{args}}

remove-bridge *args:
    ./app/scripts/remove_bridge {{args}}
