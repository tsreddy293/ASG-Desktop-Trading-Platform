from PySide6.QtGui import QColor, QPalette
from PySide6.QtCore import Qt


class AppStyles:
    """Central styling definitions for the application UI."""

    DARK_BACKGROUND = "#0f172a"
    PANEL_BACKGROUND = "#111827"
    CARD_BACKGROUND = "#1f2937"
    ACCENT = "#38bdf8"
    ACCENT_DARK = "#0ea5e9"
    TEXT_PRIMARY = "#f8fafc"
    TEXT_SECONDARY = "#cbd5e1"
    BORDER = "#334155"

    @staticmethod
    def apply_theme(app) -> None:
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(AppStyles.DARK_BACKGROUND))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(AppStyles.TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.Base, QColor(AppStyles.CARD_BACKGROUND))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(AppStyles.PANEL_BACKGROUND))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(AppStyles.CARD_BACKGROUND))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(AppStyles.TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.Text, QColor(AppStyles.TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.Button, QColor(AppStyles.PANEL_BACKGROUND))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(AppStyles.TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(AppStyles.ACCENT))
        palette.setColor(QPalette.ColorRole.Link, QColor(AppStyles.ACCENT))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(AppStyles.ACCENT))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(AppStyles.TEXT_PRIMARY))
        app.setPalette(palette)
        app.setStyle("Fusion")
        app.setStyleSheet(
            "* { font-family: 'Noto Sans Telugu', 'Nirmala UI', 'Noto Sans Devanagari', 'Segoe UI', sans-serif; }"
        )
