from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout

from src.core.translation import t


class SplashScreen(QDialog):
    """Application splash screen shown during startup."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.resize(700, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel(t("splash.title"))
        title.setStyleSheet("font-size: 28px; font-weight: 700; color: #f8fafc;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel(t("splash.subtitle"))
        subtitle.setStyleSheet("font-size: 14px; color: #cbd5e1;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.status_label = QLabel(t("splash.loading_config"))
        self.status_label.setStyleSheet("font-size: 13px; color: #f8fafc;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(8)

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress)
        layout.addStretch()

        self.setStyleSheet(
            "QDialog { background: #111827; border: 2px solid #38bdf8; border-radius: 16px; }"
        )

    def update_status(self, text: str, value: int) -> None:
        self.status_label.setText(text)
        self.progress.setValue(value)
        self.repaint()
