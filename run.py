import os
from app import create_app
from dotenv import load_dotenv

load_dotenv()
app = create_app()


if __name__ == '__main__':
    host = os.environ.get("HOST", "localhost")
    port = int(os.environ.get("PORT", 5000))
    app.run(host=host, port=port, debug=True)
