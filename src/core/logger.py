from pathlib import Path

from loguru import logger

from src.core.config import config


class AppLogger:
    """Central logging service for the application."""

    def __init__(self) -> None:
        self.log_path = Path(config.get("log_file", "logs/asg.log"))
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.remove()
        logger.add(
            self.log_path,
            rotation="10 MB",
            retention="30 days",
            level="DEBUG",
            enqueue=True,
            backtrace=True,
            diagnose=True,
        )

    def info(self, message: str) -> None:
        logger.info(message)

    def warning(self, message: str) -> None:
        logger.warning(message)

    def error(self, message: str) -> None:
        logger.error(message)

    def debug(self, message: str) -> None:
        logger.debug(message)


app_logger = AppLogger()
