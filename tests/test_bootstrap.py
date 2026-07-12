from pathlib import Path

from src.core.config import config
from src.core.database import database_manager


def test_config_and_database_bootstrap() -> None:
    assert config.get("app_name") == "AI Stock Guardian"
    assert database_manager.database_path.exists()
    assert Path("logs").exists()
