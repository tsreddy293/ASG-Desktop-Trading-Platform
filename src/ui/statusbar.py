from PySide6.QtWidgets import QLabel, QStatusBar

from src.core.config import config
from src.core.translation import t


class AppStatusBar(QStatusBar):
    """Bottom status bar for system state and notifications."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet("QStatusBar { background: #111827; color: #cbd5e1; border-top: 1px solid #334155; }")

        self.system_label = QLabel(t("status.system_ready"))
        self.version_label = QLabel(t("status.app_version", version=config.get("version", "0.2.0")))
        self.addWidget(self.system_label)
        self.addPermanentWidget(self.version_label)

    def update_translations(self) -> None:
        self.system_label.setText(t("status.system_ready"))
        self.version_label.setText(t("status.app_version", version=config.get("version", "0.2.0")))
