from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from src.core.config import config

Base = declarative_base()


class DatabaseManager:
    """Database manager for the SQLite-backed application."""

    def __init__(self, database_path: str | None = None) -> None:
        self.database_path = Path(database_path or config.get("database", "database/asg.db"))
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{self.database_path}")
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.initialize()

    def initialize(self) -> None:
        Base.metadata.create_all(self.engine)
        with self.engine.begin() as connection:
            connection.execute(text("SELECT 1"))

    def get_session(self):
        return self.SessionLocal()


database_manager = DatabaseManager()
