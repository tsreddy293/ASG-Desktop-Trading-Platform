from src.core.config import config
from src.core.translation import translation_service


def test_translation_service_switch_and_persist_language() -> None:
    original = translation_service.current_language()
    try:
        translation_service.set_language("te")
        assert translation_service.current_language() == "te"
        assert config.get("language") == "te"
    finally:
        translation_service.set_language(original)


def test_translation_service_falls_back_to_english_for_missing_key() -> None:
    original = translation_service.current_language()
    try:
        translation_service.set_language("hi")
        assert translation_service.translate("live_market.col.symbol") == "Symbol"
    finally:
        translation_service.set_language(original)
