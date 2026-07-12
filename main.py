import sys

from src.app import create_app


if __name__ == "__main__":
    app = create_app()
    sys.exit(app.run())