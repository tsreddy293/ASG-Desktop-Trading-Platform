from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.chart.model import ChartPayload
from src.chart.widget import ChartWidget


class ChartView(QWidget):
    """MVVM chart view with controls, drawing tools and status strip."""

    symbol_changed = Signal(str)
    timeframe_changed = Signal(str)
    indicator_toggled = Signal(str, bool)
    chart_type_changed = Signal(str)
    drawing_tool_changed = Signal(str)
    clear_drawings_requested = Signal()
    auto_refresh_toggled = Signal(bool)
    refresh_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        top = QFrame(self)
        top.setStyleSheet("QFrame { background: #111827; border: 1px solid #334155; border-radius: 10px; }")
        top_layout = QVBoxLayout(top)
        top_layout.setContentsMargins(10, 8, 10, 8)
        top_layout.setSpacing(8)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Symbol"))

        self.symbol_input = QLineEdit("SBIN")
        self.symbol_input.setFixedWidth(120)
        self.symbol_input.returnPressed.connect(self._emit_symbol_change)
        self.symbol_input.setStyleSheet("QLineEdit { background: #0b1220; border: 1px solid #334155; border-radius: 6px; padding: 4px 6px; color: #f8fafc; }")
        row1.addWidget(self.symbol_input)

        self.apply_symbol_btn = QPushButton("Apply")
        self.apply_symbol_btn.clicked.connect(self._emit_symbol_change)
        row1.addWidget(self.apply_symbol_btn)

        row1.addSpacing(12)
        row1.addWidget(QLabel("Type"))
        self.chart_type_group = QButtonGroup(self)
        for name in ["Candlestick", "Line", "Area"]:
            button = QPushButton(name)
            button.setCheckable(True)
            if name == "Candlestick":
                button.setChecked(True)
            button.clicked.connect(lambda checked, n=name: self.chart_type_changed.emit(n))
            button.setStyleSheet(
                "QPushButton { background: #1f2937; color: #cbd5e1; border-radius: 6px; border: 1px solid #334155; padding: 4px 8px; }"
                "QPushButton:checked { background: #38bdf8; color: #0f172a; border: 1px solid #38bdf8; }"
            )
            self.chart_type_group.addButton(button)
            row1.addWidget(button)

        row1.addSpacing(12)
        row1.addWidget(QLabel("Draw"))
        self.tool_group = QButtonGroup(self)
        for name in ["None", "Trend Line", "Horizontal Line", "Vertical Line", "Rectangle"]:
            button = QPushButton(name)
            button.setCheckable(True)
            if name == "None":
                button.setChecked(True)
            button.clicked.connect(lambda checked, n=name: self.drawing_tool_changed.emit(n))
            button.setStyleSheet(
                "QPushButton { background: #1f2937; color: #cbd5e1; border-radius: 6px; border: 1px solid #334155; padding: 4px 8px; }"
                "QPushButton:checked { background: #22d3ee; color: #082f49; border: 1px solid #22d3ee; }"
            )
            self.tool_group.addButton(button)
            row1.addWidget(button)

        self.clear_draw_btn = QPushButton("Clear Drawings")
        self.clear_draw_btn.clicked.connect(self.clear_drawings_requested.emit)
        row1.addWidget(self.clear_draw_btn)

        row1.addStretch()

        self.auto_refresh_box = QCheckBox("Auto Refresh")
        self.auto_refresh_box.setChecked(True)
        self.auto_refresh_box.toggled.connect(self.auto_refresh_toggled.emit)
        row1.addWidget(self.auto_refresh_box)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        self.refresh_btn.setStyleSheet("background: #38bdf8; color: #0f172a; border-radius: 6px; padding: 6px 10px;")
        row1.addWidget(self.refresh_btn)

        top_layout.addLayout(row1)

        row2 = QHBoxLayout()
        tf_group = QButtonGroup(self)
        tf_group.setExclusive(True)
        self._tf_buttons: dict[str, QPushButton] = {}
        for tf in ["1m", "5m", "15m", "30m", "1H", "1D"]:
            button = QPushButton(tf)
            button.setCheckable(True)
            button.setStyleSheet(
                "QPushButton { background: #1f2937; color: #cbd5e1; border-radius: 6px; border: 1px solid #334155; padding: 4px 8px; }"
                "QPushButton:checked { background: #38bdf8; color: #0f172a; border: 1px solid #38bdf8; }"
            )
            button.clicked.connect(lambda checked, label=tf: self.timeframe_changed.emit(label))
            tf_group.addButton(button)
            self._tf_buttons[tf] = button
            row2.addWidget(button)
        self._tf_buttons["15m"].setChecked(True)

        row2.addSpacing(12)
        row2.addWidget(QLabel("Indicators"))

        indicators_container = QWidget()
        indicators_layout = QHBoxLayout(indicators_container)
        indicators_layout.setContentsMargins(0, 0, 0, 0)
        indicators_layout.setSpacing(8)
        self._indicator_boxes: dict[str, QCheckBox] = {}
        for name in ["EMA", "SMA", "VWAP", "RSI", "MACD", "SuperTrend", "Bollinger Bands"]:
            box = QCheckBox(name)
            box.setStyleSheet("QCheckBox { color: #cbd5e1; }")
            box.setChecked(name in {"EMA", "SMA", "VWAP"})
            box.toggled.connect(lambda checked, indicator=name: self.indicator_toggled.emit(indicator, checked))
            indicators_layout.addWidget(box)
            self._indicator_boxes[name] = box

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(indicators_container)

        row2.addWidget(scroll, 1)
        top_layout.addLayout(row2)

        root.addWidget(top)

        self.chart_widget = ChartWidget(self)
        self.chart_widget.setStyleSheet("border: 1px solid #334155; border-radius: 10px;")
        root.addWidget(self.chart_widget, 1)

        status_strip = QFrame(self)
        status_strip.setStyleSheet("QFrame { background: #0b1220; border: 1px solid #334155; border-radius: 8px; }")
        status_layout = QHBoxLayout(status_strip)
        status_layout.setContentsMargins(10, 6, 10, 6)

        self.connection_label = QLabel("Disconnected")
        self.connection_label.setStyleSheet("color: #ef4444; font-weight: 700;")
        self.last_updated_label = QLabel("Last Updated: --")
        self.last_updated_label.setStyleSheet("color: #94a3b8;")
        self.ohlc_label = QLabel("OHLC: --")
        self.ohlc_label.setStyleSheet("color: #cbd5e1;")

        status_layout.addWidget(self.connection_label)
        status_layout.addSpacing(12)
        status_layout.addWidget(self.last_updated_label)
        status_layout.addStretch()
        status_layout.addWidget(self.ohlc_label)

        root.addWidget(status_strip)

    def _emit_symbol_change(self) -> None:
        self.symbol_changed.emit(self.symbol_input.text().strip().upper())

    def render(self, payload: ChartPayload) -> None:
        self.chart_widget.set_payload(payload)
        data = payload.data
        if data.candles:
            latest = data.candles[-1]
            self.ohlc_label.setText(
                f"{data.symbol} {data.timeframe} | O:{latest.open:,.2f} H:{latest.high:,.2f} L:{latest.low:,.2f} C:{latest.close:,.2f}"
            )

    def set_chart_type(self, chart_type: str) -> None:
        self.chart_widget.set_chart_type(chart_type)

    def set_drawing_tool(self, tool: str) -> None:
        self.chart_widget.set_drawing_tool(tool)

    def clear_drawings(self) -> None:
        self.chart_widget.clear_drawings()

    def set_status(self, status_text: str, updated_text: str) -> None:
        self.connection_label.setText(status_text)
        if status_text.startswith("Connected"):
            self.connection_label.setStyleSheet("color: #22c55e; font-weight: 700;")
        else:
            self.connection_label.setStyleSheet("color: #ef4444; font-weight: 700;")
        self.last_updated_label.setText(f"Last Updated: {updated_text}")
