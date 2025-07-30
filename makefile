dev:
	FLASK_ENV=development python3 run.py

prod:
	FLASK_ENV=production gunicorn "app:create_app()" --bind 0.0.0.0:8000 --workers 4
