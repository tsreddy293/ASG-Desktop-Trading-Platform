import json
from pathlib import Path
from typing import Any

from src.core.constants import APP_NAME, APP_VERSION, DATABASE_PATH, DEFAULT_LANGUAGE, DEFAULT_THEME, LOG_PATH


class ConfigManager:
    """Manages application configuration from config/config.json."""

    def __init__(self, config_path: str | None = None) -> None:
        self.config_path = Path(config_path or "config/config.json")
        self.config: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        if not self.config_path.exists():
            self.config = self._default_config()
            self.save()
            return

        with self.config_path.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)

        defaults = self._default_config()
        defaults.update(loaded)
        self.config = defaults
        self.save()

    def save(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w", encoding="utf-8") as handle:
            json.dump(self.config, handle, indent=4)

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.config[key] = value
        self.save()

    def _default_config(self) -> dict[str, Any]:
        return {
            "app_name": APP_NAME,
            "version": APP_VERSION,
            "language": DEFAULT_LANGUAGE,
            "theme": DEFAULT_THEME,
            "database": DATABASE_PATH,
            "log_file": LOG_PATH,
            "broker": "",
            "default_broker": "fivepaisa",
            "market_refresh_interval_seconds": 5,
        }


config = ConfigManager()
