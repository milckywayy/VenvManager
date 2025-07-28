dev:
	FLASK_ENV=development python3 run.py

prod:
	FLASK_ENV=production gunicorn "app:create_app()" --bind 0.0.0.0:8000 --workers 4

win-dev:
	set FLASK_ENV=development&& python run.py

win-prod:
	set FLASK_ENV=production&& python -m waitress --call --host=0.0.0.0 --port=8080 app:create_app
