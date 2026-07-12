import json
from pathlib import Path


class ConfigManager:
    def __init__(self):
        self.config_path = Path("config/config.json")
        self.config = {}
        self.load()

    def load(self):
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

    def get(self, key):
        return self.config.get(key)

    def set(self, key, value):
        self.config[key] = value
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)


config = ConfigManager()