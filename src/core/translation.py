from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from src.core.config import config
from src.core.logger import app_logger


class TranslationService(QObject):
    """Loads language resources and provides runtime translation with fallback."""

    language_changed = Signal(str)

    SUPPORTED = {
        "en": "English",
        "te": "తెలుగు",
        "hi": "हिन्दी",
    }

    def __init__(self) -> None:
        super().__init__()
        self._lang_dir = Path("resources/lang")
        self._cache: dict[str, dict[str, str]] = {}
        self._current = "en"
        self._load_all()

        configured = str(config.get("language", "en") or "en").strip().lower()
        if configured in self.SUPPORTED:
            self._current = configured

    def _load_all(self) -> None:
        self._cache.clear()
        for code in self.SUPPORTED:
            path = self._lang_dir / f"{code}.json"
            if not path.exists():
                self._cache[code] = {}
                continue
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            self._cache[code] = {str(k): str(v) for k, v in data.items()}

    def translate(self, key: str, **kwargs) -> str:
        current_map = self._cache.get(self._current, {})
        fallback_map = self._cache.get("en", {})
        template = current_map.get(key, fallback_map.get(key, key))
        try:
            return template.format(**kwargs)
        except Exception:
            return template

    def set_language(self, language: str) -> None:
        code = (language or "").strip().lower()
        if code not in self.SUPPORTED:
            code = "en"
        if code == self._current:
            return

        self._current = code
        config.set("language", code)
        app_logger.info(f"Language changed to {code}")
        self.language_changed.emit(code)

    def current_language(self) -> str:
        return self._current


translation_service = TranslationService()


def t(key: str, **kwargs) -> str:
    return translation_service.translate(key, **kwargs)
