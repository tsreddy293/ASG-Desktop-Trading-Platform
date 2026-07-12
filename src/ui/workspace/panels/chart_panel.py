from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from src.ui.workspace.viewmodels.workspace_viewmodels import ChartPanelViewModel


class ChartPanel(QWidget):
    def __init__(self, viewmodel: ChartPanelViewModel | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vm = viewmodel or ChartPanelViewModel()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        top = QHBoxLayout()
        self.symbol_input = QLineEdit("SBIN")
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(["1m", "5m", "15m", "30m", "1H", "1D"])
        self.apply_btn = QPushButton("Apply")
        top.addWidget(QLabel("Symbol"))
        top.addWidget(self.symbol_input)
        top.addWidget(QLabel("Timeframe"))
        top.addWidget(self.timeframe_combo)
        top.addWidget(self.apply_btn)

        self.canvas = QFrame(self)
        self.canvas.setStyleSheet("QFrame { background: #0b1220; border: 1px solid #334155; border-radius: 10px; }")
        canvas_layout = QVBoxLayout(self.canvas)
        self.state_label = QLabel("Professional Chart Area")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_label.setStyleSheet("font-size: 18px; color: #7dd3fc;")
        canvas_layout.addWidget(self.state_label)

        layout.addLayout(top)
        layout.addWidget(self.canvas, 1)

        self.apply_btn.clicked.connect(self._apply)
        self.timeframe_combo.currentTextChanged.connect(self._vm.set_timeframe)
        self._vm.chartStateUpdated.connect(self._render)
        self._vm.refresh()

    def _apply(self) -> None:
        self._vm.set_symbol(self.symbol_input.text())

    def _render(self, state: dict) -> None:
        self.state_label.setText(
            f"{state.get('symbol', '--')} | {state.get('timeframe', '--')} | {state.get('chart_type', '--')} | {state.get('status', '--')}"
        )
