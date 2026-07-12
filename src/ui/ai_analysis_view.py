from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.analysis.model import AIAnalysisSnapshot
from src.core.translation import t


class MiniCandlestickChart(QWidget):
    """Compact candlestick chart widget used in AI analysis bottom panel."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._candles: list[tuple[float, float, float, float]] = []
        self.setMinimumHeight(170)

    def set_candles(self, candles: list[tuple[float, float, float, float]]) -> None:
        self._candles = candles
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#0b1220"))

        if not self._candles:
            painter.setPen(QColor("#64748b"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, t("ai.no_candle_data"))
            return

        highs = [item[1] for item in self._candles]
        lows = [item[2] for item in self._candles]
        max_price = max(highs)
        min_price = min(lows)
        price_range = max(0.001, max_price - min_price)

        margin_x = 14
        margin_y = 14
        width = max(1, self.width() - (margin_x * 2))
        height = max(1, self.height() - (margin_y * 2))
        candle_width = max(3.0, width / (len(self._candles) * 1.6))
        gap = (width / len(self._candles))

        for index, (open_price, high_price, low_price, close_price) in enumerate(self._candles):
            x_center = margin_x + (index * gap) + gap / 2
            y_high = margin_y + ((max_price - high_price) / price_range) * height
            y_low = margin_y + ((max_price - low_price) / price_range) * height
            y_open = margin_y + ((max_price - open_price) / price_range) * height
            y_close = margin_y + ((max_price - close_price) / price_range) * height

            bullish = close_price >= open_price
            color = QColor("#22c55e") if bullish else QColor("#ef4444")
            painter.setPen(QPen(color, 1.4))
            painter.drawLine(int(x_center), int(y_high), int(x_center), int(y_low))

            top = min(y_open, y_close)
            bottom = max(y_open, y_close)
            rect = QRectF(x_center - candle_width / 2, top, candle_width, max(2.0, bottom - top))
            painter.fillRect(rect, color)


class AIAnalysisView(QWidget):
    """Professional AI Analysis page with institutional multi-panel layout."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        left_panel = QVBoxLayout()
        left_panel.setSpacing(12)

        top = self._create_card()
        top_layout = QGridLayout(top)
        top_layout.setContentsMargins(14, 12, 14, 12)
        top_layout.setHorizontalSpacing(22)
        top_layout.setVerticalSpacing(10)

        self.stock_name = self._value_label()
        self.exchange = self._value_label()
        self.sector = self._value_label()
        self.current_price = self._value_label()
        self.todays_change = self._value_label()
        self.volume = self._value_label()

        top_layout.addWidget(QLabel(t("ai.stock_name")), 0, 0)
        top_layout.addWidget(self.stock_name, 0, 1)
        top_layout.addWidget(QLabel(t("ai.exchange")), 0, 2)
        top_layout.addWidget(self.exchange, 0, 3)
        top_layout.addWidget(QLabel(t("ai.sector")), 0, 4)
        top_layout.addWidget(self.sector, 0, 5)
        top_layout.addWidget(QLabel(t("ai.current_price")), 1, 0)
        top_layout.addWidget(self.current_price, 1, 1)
        top_layout.addWidget(QLabel(t("ai.todays_change")), 1, 2)
        top_layout.addWidget(self.todays_change, 1, 3)
        top_layout.addWidget(QLabel(t("ai.volume")), 1, 4)
        top_layout.addWidget(self.volume, 1, 5)
        left_panel.addWidget(top)

        middle = self._create_card()
        mid_layout = QGridLayout(middle)
        mid_layout.setContentsMargins(14, 12, 14, 12)
        mid_layout.setHorizontalSpacing(20)
        mid_layout.setVerticalSpacing(10)

        self.signal_badge = QLabel(t("ai.signal.hold"))
        self.signal_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.signal_badge.setMinimumHeight(52)
        self.signal_badge.setStyleSheet("font-size: 24px; font-weight: 800; border-radius: 8px; background: #eab308; color: #111827;")

        self.ai_score = self._value_label()
        self.confidence = self._value_label()
        self.trend = self._value_label()
        self.risk = self._value_label()
        self.support = self._value_label()
        self.resistance = self._value_label()
        self.target_1 = self._value_label()
        self.target_2 = self._value_label()
        self.stoploss = self._value_label()

        mid_layout.addWidget(self.signal_badge, 0, 0, 2, 2)
        mid_layout.addWidget(QLabel(t("ai.score")), 0, 2)
        mid_layout.addWidget(self.ai_score, 0, 3)
        mid_layout.addWidget(QLabel(t("ai.confidence")), 0, 4)
        mid_layout.addWidget(self.confidence, 0, 5)
        mid_layout.addWidget(QLabel(t("ai.trend")), 1, 2)
        mid_layout.addWidget(self.trend, 1, 3)
        mid_layout.addWidget(QLabel(t("ai.risk")), 1, 4)
        mid_layout.addWidget(self.risk, 1, 5)
        mid_layout.addWidget(QLabel(t("ai.support")), 2, 0)
        mid_layout.addWidget(self.support, 2, 1)
        mid_layout.addWidget(QLabel(t("ai.resistance")), 2, 2)
        mid_layout.addWidget(self.resistance, 2, 3)
        mid_layout.addWidget(QLabel(t("ai.target1")), 2, 4)
        mid_layout.addWidget(self.target_1, 2, 5)
        mid_layout.addWidget(QLabel(t("ai.target2")), 3, 0)
        mid_layout.addWidget(self.target_2, 3, 1)
        mid_layout.addWidget(QLabel(t("ai.stoploss")), 3, 2)
        mid_layout.addWidget(self.stoploss, 3, 3)
        left_panel.addWidget(middle)

        indicators = self._create_card()
        ind_layout = QGridLayout(indicators)
        ind_layout.setContentsMargins(14, 12, 14, 12)
        ind_layout.setHorizontalSpacing(20)
        ind_layout.setVerticalSpacing(10)

        self.rsi = self._value_label()
        self.macd = self._value_label()
        self.ema = self._value_label()
        self.vwap = self._value_label()
        self.adx = self._value_label()
        self.atr = self._value_label()
        self.supertrend = self._value_label()
        self.delivery = self._value_label()
        self.volume_analysis = self._value_label(multiline=True)

        ind_layout.addWidget(QLabel("RSI"), 0, 0)
        ind_layout.addWidget(self.rsi, 0, 1)
        ind_layout.addWidget(QLabel("MACD"), 0, 2)
        ind_layout.addWidget(self.macd, 0, 3)
        ind_layout.addWidget(QLabel("EMA"), 1, 0)
        ind_layout.addWidget(self.ema, 1, 1, 1, 3)
        ind_layout.addWidget(QLabel("VWAP"), 2, 0)
        ind_layout.addWidget(self.vwap, 2, 1)
        ind_layout.addWidget(QLabel("ADX"), 2, 2)
        ind_layout.addWidget(self.adx, 2, 3)
        ind_layout.addWidget(QLabel("ATR"), 3, 0)
        ind_layout.addWidget(self.atr, 3, 1)
        ind_layout.addWidget(QLabel("SuperTrend"), 3, 2)
        ind_layout.addWidget(self.supertrend, 3, 3)
        ind_layout.addWidget(QLabel(t("ai.delivery")), 4, 0)
        ind_layout.addWidget(self.delivery, 4, 1)
        ind_layout.addWidget(QLabel(t("ai.volume_analysis")), 4, 2)
        ind_layout.addWidget(self.volume_analysis, 4, 3)
        left_panel.addWidget(indicators)

        bottom = self._create_card()
        bot_layout = QGridLayout(bottom)
        bot_layout.setContentsMargins(14, 12, 14, 12)
        bot_layout.setHorizontalSpacing(16)
        bot_layout.setVerticalSpacing(10)

        self.reasons_list = QListWidget()
        self.reasons_list.setStyleSheet("QListWidget { background: #0b1220; border: 1px solid #334155; border-radius: 8px; color: #f8fafc; }")

        self.ai_summary = QTextEdit()
        self.ai_summary.setReadOnly(True)
        self.ai_summary.setStyleSheet("QTextEdit { background: #0b1220; border: 1px solid #334155; border-radius: 8px; color: #f8fafc; }")
        self.ai_summary.setMinimumHeight(90)

        self.recent_signals = QListWidget()
        self.recent_signals.setStyleSheet("QListWidget { background: #0b1220; border: 1px solid #334155; border-radius: 8px; color: #f8fafc; }")

        self.candle_chart = MiniCandlestickChart()
        self.candle_chart.setStyleSheet("border: 1px solid #334155; border-radius: 8px;")

        bot_layout.addWidget(QLabel(t("ai.recommendation.heading")), 0, 0)
        bot_layout.addWidget(QLabel(t("ai.summary.heading")), 0, 1)
        bot_layout.addWidget(QLabel(t("ai.recent_signals")), 0, 2)
        bot_layout.addWidget(self.reasons_list, 1, 0)
        bot_layout.addWidget(self.ai_summary, 1, 1)
        bot_layout.addWidget(self.recent_signals, 1, 2)
        bot_layout.addWidget(QLabel(t("ai.mini_chart")), 2, 0, 1, 3)
        bot_layout.addWidget(self.candle_chart, 3, 0, 1, 3)
        left_panel.addWidget(bottom)

        right = self._create_card()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(14, 12, 14, 12)
        right_layout.setSpacing(10)

        self.right_trend_strength = self._metric_tile(t("ai.metric.trend_strength"))
        self.right_momentum = self._metric_tile(t("ai.metric.momentum"))
        self.right_volume_strength = self._metric_tile(t("ai.metric.volume_strength"))
        self.right_confidence = self._metric_tile(t("ai.metric.confidence"))

        right_layout.addWidget(self.right_trend_strength)
        right_layout.addWidget(self.right_momentum)
        right_layout.addWidget(self.right_volume_strength)
        right_layout.addWidget(self.right_confidence)
        right_layout.addStretch()

        root.addLayout(left_panel, 4)
        root.addWidget(right, 1)

    def render_analysis(self, snapshot: AIAnalysisSnapshot) -> None:
        self.stock_name.setText(snapshot.stock_name)
        self.exchange.setText(snapshot.exchange)
        self.sector.setText(snapshot.sector)
        self.current_price.setText(f"{snapshot.current_price:,.2f}")
        self.todays_change.setText(f"{snapshot.todays_change_percent:+.2f}%")
        self.volume.setText(f"{snapshot.volume:,}")

        self.signal_badge.setText(self._translate_signal(snapshot.signal))
        if snapshot.signal in {"BUY", "STRONG BUY"}:
            self.signal_badge.setStyleSheet("font-size: 24px; font-weight: 800; border-radius: 8px; background: #22c55e; color: #0b1220;")
        elif snapshot.signal in {"SELL", "STRONG SELL"}:
            self.signal_badge.setStyleSheet("font-size: 24px; font-weight: 800; border-radius: 8px; background: #ef4444; color: #ffffff;")
        elif snapshot.signal == "NO DATA":
            self.signal_badge.setStyleSheet("font-size: 24px; font-weight: 800; border-radius: 8px; background: #64748b; color: #ffffff;")
        else:
            self.signal_badge.setStyleSheet("font-size: 24px; font-weight: 800; border-radius: 8px; background: #eab308; color: #111827;")

        self.ai_score.setText(f"{snapshot.ai_score}/100")
        self.confidence.setText(f"{snapshot.confidence_percent:.1f}%")
        self.trend.setText(snapshot.trend)
        self.risk.setText(snapshot.risk)
        self.support.setText(f"{snapshot.support:,.2f}")
        self.resistance.setText(f"{snapshot.resistance:,.2f}")
        self.target_1.setText(f"{snapshot.target_1:,.2f}")
        self.target_2.setText(f"{snapshot.target_2:,.2f}")
        self.stoploss.setText(f"{snapshot.stop_loss:,.2f}")

        self.rsi.setText(f"{snapshot.rsi:.1f}")
        self.macd.setText(f"{snapshot.macd:+.2f}")
        self.ema.setText(snapshot.ema)
        self.vwap.setText(snapshot.vwap)
        self.adx.setText(f"{snapshot.adx:.1f}")
        self.atr.setText(f"{snapshot.atr:.2f}")
        self.supertrend.setText(snapshot.supertrend)
        self.delivery.setText(f"{snapshot.delivery_percent:.1f}%")
        self.volume_analysis.setText(snapshot.volume_analysis)

        self.reasons_list.clear()
        for reason in snapshot.reasons:
            self.reasons_list.addItem(QListWidgetItem(reason))

        self.ai_summary.setText(snapshot.ai_summary)

        self.recent_signals.clear()
        for signal in snapshot.recent_signals:
            self.recent_signals.addItem(QListWidgetItem(signal))

        self.candle_chart.set_candles(snapshot.candles)

        self._set_metric_tile(self.right_trend_strength, t("ai.metric.trend_strength"), snapshot.trend_strength)
        self._set_metric_tile(self.right_momentum, t("ai.metric.momentum"), snapshot.momentum)
        self._set_metric_tile(self.right_volume_strength, t("ai.metric.volume_strength"), snapshot.volume_strength)
        self._set_metric_tile(self.right_confidence, t("ai.metric.confidence"), snapshot.confidence_meter)

    @staticmethod
    def _create_card() -> QFrame:
        card = QFrame()
        card.setStyleSheet("QFrame { background: #111827; border: 1px solid #334155; border-radius: 10px; }")
        return card

    @staticmethod
    def _value_label(multiline: bool = False) -> QLabel:
        lbl = QLabel("--")
        lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #f8fafc;")
        if multiline:
            lbl.setWordWrap(True)
        return lbl

    @staticmethod
    def _metric_tile(title: str) -> QFrame:
        tile = QFrame()
        tile.setStyleSheet("QFrame { background: #0b1220; border: 1px solid #334155; border-radius: 8px; }")
        layout = QVBoxLayout(tile)
        layout.setContentsMargins(10, 10, 10, 10)
        label_title = QLabel(title)
        label_title.setStyleSheet("color: #94a3b8; font-size: 12px;")
        label_value = QLabel("0")
        label_value.setStyleSheet("color: #f8fafc; font-size: 24px; font-weight: 800;")
        layout.addWidget(label_title)
        layout.addWidget(label_value)
        tile.setProperty("metric_value_label", label_value)
        return tile

    @staticmethod
    def _set_metric_tile(tile: QFrame, title: str, value: int) -> None:
        layout = tile.layout()
        if layout is None:
            return
        title_label = layout.itemAt(0).widget()
        value_label = layout.itemAt(1).widget()
        if isinstance(title_label, QLabel):
            title_label.setText(title)
        if isinstance(value_label, QLabel):
            value_label.setText(f"{value}")

    @staticmethod
    def _translate_signal(signal: str) -> str:
        key_map = {
            "STRONG BUY": "ai.signal.strong_buy",
            "BUY": "ai.signal.buy",
            "HOLD": "ai.signal.hold",
            "SELL": "ai.signal.sell",
            "STRONG SELL": "ai.signal.strong_sell",
            "NO DATA": "ai.signal.no_data",
        }
        return t(key_map.get(signal, "ai.signal.hold"))
