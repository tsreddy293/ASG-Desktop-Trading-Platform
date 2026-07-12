from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen, QWheelEvent
from PySide6.QtWidgets import QWidget

from src.chart.model import ChartPayload


@dataclass(slots=True)
class DrawingObject:
    tool: str
    start: QPoint
    end: QPoint


class ChartWidget(QWidget):
    """Professional chart widget supporting chart modes, drawings and interactions."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self._payload: ChartPayload | None = None
        self._hover_pos: QPoint | None = None
        self._drag_start: QPoint | None = None
        self._pan_offset = 0
        self._zoom = 1.0

        self._chart_type = "Candlestick"
        self._active_tool = "None"
        self._drawings: list[DrawingObject] = []
        self._drawing_start: QPoint | None = None
        self._drawing_preview_end: QPoint | None = None
        self._drawing_text_default = "Note"

    def set_payload(self, payload: ChartPayload) -> None:
        self._payload = payload
        self.update()

    def set_chart_type(self, chart_type: str) -> None:
        self._chart_type = chart_type
        self.update()

    def set_drawing_tool(self, tool: str) -> None:
        self._active_tool = tool

    def clear_drawings(self) -> None:
        self._drawings.clear()
        self.update()

    def reset_zoom(self) -> None:
        self._zoom = 1.0
        self._pan_offset = 0
        self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.angleDelta().y() > 0:
            self._zoom = min(4.0, self._zoom * 1.12)
        else:
            self._zoom = max(0.45, self._zoom / 1.12)
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._hover_pos = event.pos()
        if self._drawing_start is not None:
            self._drawing_preview_end = event.pos()
            self.update()
            return

        if self._drag_start is not None and self._active_tool == "None":
            delta = event.pos().x() - self._drag_start.x()
            self._pan_offset -= int(delta / 12)
            self._drag_start = event.pos()
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._active_tool != "None":
            self._drawing_start = event.pos()
            self._drawing_preview_end = event.pos()
            return
        self._drag_start = event.pos()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self._drawing_start is not None and self._active_tool != "None":
            end = event.pos()
            self._drawings.append(DrawingObject(self._active_tool, self._drawing_start, end))
            self._drawing_start = None
            self._drawing_preview_end = None
            self.update()
            return

        self._drag_start = None

    def leaveEvent(self, event) -> None:
        self._hover_pos = None
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#0b1220"))

        payload = self._payload
        if payload is None or not payload.data.candles:
            painter.setPen(QColor("#64748b"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No chart data")
            return

        candles = payload.data.candles
        visible = max(20, min(len(candles), int(len(candles) / self._zoom)))
        max_start = max(0, len(candles) - visible)
        start = max(0, min(max_start, max_start - self._pan_offset))
        view = candles[start : start + visible]
        max_points = max(120, int(max(120.0, self.width() - 160)))
        draw_view = self._decimate_if_needed(view, max_points=max_points)

        chart_left = 54
        chart_top = 24
        chart_right = self.width() - 70
        chart_bottom = int(self.height() * 0.72)
        vol_top = chart_bottom + 24
        vol_bottom = self.height() - 34

        price_area = QRectF(chart_left, chart_top, chart_right - chart_left, chart_bottom - chart_top)
        vol_area = QRectF(chart_left, vol_top, chart_right - chart_left, vol_bottom - vol_top)

        self._draw_grid(painter, price_area)
        self._draw_grid(painter, vol_area)

        max_price = max(c.high for c in draw_view)
        min_price = min(c.low for c in draw_view)
        prange = max(0.01, max_price - min_price)
        max_vol = max(c.volume for c in draw_view)

        step_x = price_area.width() / max(1, len(draw_view))
        body_w = max(3.0, step_x * 0.58)

        if self._chart_type == "Candlestick":
            self._draw_candles(painter, draw_view, price_area, vol_area, max_price, prange, max_vol, step_x, body_w)
        elif self._chart_type == "Line":
            self._draw_line_chart(painter, draw_view, price_area, max_price, prange, step_x)
            self._draw_volume_bars(painter, draw_view, vol_area, max_vol, step_x, body_w)
        elif self._chart_type == "OHLC":
            self._draw_ohlc_chart(painter, draw_view, price_area, vol_area, max_price, prange, max_vol, step_x)
        elif self._chart_type == "Heikin Ashi":
            ha = self._to_heikin_ashi(draw_view)
            self._draw_candles(painter, ha, price_area, vol_area, max_price, prange, max_vol, step_x, body_w)
        else:
            self._draw_area_chart(painter, draw_view, price_area, max_price, prange, step_x)
            self._draw_volume_bars(painter, draw_view, vol_area, max_vol, step_x, body_w)

        self._draw_indicator_lines(painter, payload, draw_view, start, price_area, max_price, prange, step_x)
        self._draw_axes(painter, draw_view, price_area, vol_area, max_price, min_price)
        self._draw_last_price_line(painter, payload.last_price, price_area, max_price, prange)
        self._draw_ohlc_hover(painter, draw_view, price_area, step_x)
        self._draw_drawings(painter)
        self._draw_preview_drawing(painter)

    @staticmethod
    def _decimate_if_needed(candles, max_points: int):
        if len(candles) <= max_points:
            return candles
        stride = max(1, (len(candles) + max_points - 1) // max_points)
        return [candles[i] for i in range(0, len(candles), stride)]

    def _to_heikin_ashi(self, candles):
        if not candles:
            return candles
        converted = []
        prev_open = candles[0].open
        prev_close = candles[0].close
        for candle in candles:
            ha_close = (candle.open + candle.high + candle.low + candle.close) / 4
            ha_open = (prev_open + prev_close) / 2
            ha_high = max(candle.high, ha_open, ha_close)
            ha_low = min(candle.low, ha_open, ha_close)
            converted.append(type(candle)(timestamp=candle.timestamp, open=ha_open, high=ha_high, low=ha_low, close=ha_close, volume=candle.volume))
            prev_open = ha_open
            prev_close = ha_close
        return converted

    def _draw_candles(self, painter: QPainter, view, price_area: QRectF, vol_area: QRectF, max_price: float, prange: float, max_vol: int, step_x: float, body_w: float) -> None:
        for idx, candle in enumerate(view):
            x = price_area.left() + idx * step_x + step_x / 2
            y_high = price_area.top() + ((max_price - candle.high) / prange) * price_area.height()
            y_low = price_area.top() + ((max_price - candle.low) / prange) * price_area.height()
            y_open = price_area.top() + ((max_price - candle.open) / prange) * price_area.height()
            y_close = price_area.top() + ((max_price - candle.close) / prange) * price_area.height()

            bullish = candle.close >= candle.open
            color = QColor("#22c55e") if bullish else QColor("#ef4444")
            painter.setPen(QPen(color, 1.2))
            painter.drawLine(int(x), int(y_high), int(x), int(y_low))

            top = min(y_open, y_close)
            bottom = max(y_open, y_close)
            painter.fillRect(QRectF(x - body_w / 2, top, body_w, max(2.0, bottom - top)), color)

            vol_h = (candle.volume / max_vol) * vol_area.height() if max_vol > 0 else 0
            painter.fillRect(QRectF(x - body_w / 2, vol_area.bottom() - vol_h, body_w, vol_h), QColor("#38bdf8" if bullish else "#f97316"))

    def _draw_line_chart(self, painter: QPainter, view, price_area: QRectF, max_price: float, prange: float, step_x: float) -> None:
        painter.setPen(QPen(QColor("#60a5fa"), 1.8))
        prev = None
        for idx, candle in enumerate(view):
            x = price_area.left() + idx * step_x + step_x / 2
            y = price_area.top() + ((max_price - candle.close) / prange) * price_area.height()
            if prev is not None:
                painter.drawLine(int(prev[0]), int(prev[1]), int(x), int(y))
            prev = (x, y)

    def _draw_ohlc_chart(self, painter: QPainter, view, price_area: QRectF, vol_area: QRectF, max_price: float, prange: float, max_vol: int, step_x: float) -> None:
        for idx, candle in enumerate(view):
            x = price_area.left() + idx * step_x + step_x / 2
            y_high = price_area.top() + ((max_price - candle.high) / prange) * price_area.height()
            y_low = price_area.top() + ((max_price - candle.low) / prange) * price_area.height()
            y_open = price_area.top() + ((max_price - candle.open) / prange) * price_area.height()
            y_close = price_area.top() + ((max_price - candle.close) / prange) * price_area.height()

            bullish = candle.close >= candle.open
            color = QColor("#22c55e") if bullish else QColor("#ef4444")
            painter.setPen(QPen(color, 1.2))
            painter.drawLine(int(x), int(y_high), int(x), int(y_low))
            painter.drawLine(int(x - 4), int(y_open), int(x), int(y_open))
            painter.drawLine(int(x), int(y_close), int(x + 4), int(y_close))

            vol_h = (candle.volume / max_vol) * vol_area.height() if max_vol > 0 else 0
            painter.fillRect(QRectF(x - 1.5, vol_area.bottom() - vol_h, 3.0, vol_h), QColor("#38bdf8" if bullish else "#f97316"))

    def _draw_area_chart(self, painter: QPainter, view, price_area: QRectF, max_price: float, prange: float, step_x: float) -> None:
        from PySide6.QtGui import QPainterPath

        if not view:
            return
        path = QPainterPath()
        points = []
        for idx, candle in enumerate(view):
            x = price_area.left() + idx * step_x + step_x / 2
            y = price_area.top() + ((max_price - candle.close) / prange) * price_area.height()
            points.append((x, y))

        path.moveTo(points[0][0], points[0][1])
        for x, y in points[1:]:
            path.lineTo(x, y)

        fill_path = QPainterPath(path)
        fill_path.lineTo(points[-1][0], price_area.bottom())
        fill_path.lineTo(points[0][0], price_area.bottom())
        fill_path.closeSubpath()

        painter.fillPath(fill_path, QColor(56, 189, 248, 55))
        painter.setPen(QPen(QColor("#22d3ee"), 1.8))
        painter.drawPath(path)

    def _draw_volume_bars(self, painter: QPainter, view, vol_area: QRectF, max_vol: int, step_x: float, body_w: float) -> None:
        for idx, candle in enumerate(view):
            x = vol_area.left() + idx * step_x + step_x / 2
            vol_h = (candle.volume / max_vol) * vol_area.height() if max_vol > 0 else 0
            bullish = candle.close >= candle.open
            painter.fillRect(QRectF(x - body_w / 2, vol_area.bottom() - vol_h, body_w, vol_h), QColor("#38bdf8" if bullish else "#f97316"))

    @staticmethod
    def _draw_grid(painter: QPainter, area: QRectF) -> None:
        painter.setPen(QPen(QColor("#1f2937"), 1))
        for i in range(6):
            y = area.top() + (area.height() / 5) * i
            painter.drawLine(int(area.left()), int(y), int(area.right()), int(y))
        for i in range(8):
            x = area.left() + (area.width() / 7) * i
            painter.drawLine(int(x), int(area.top()), int(x), int(area.bottom()))

    @staticmethod
    def _series_color(name: str) -> QColor:
        palette = {
            "EMA": QColor("#f59e0b"),
            "SMA": QColor("#60a5fa"),
            "VWAP": QColor("#a78bfa"),
            "BB_MID": QColor("#eab308"),
            "BB_UPPER": QColor("#22d3ee"),
            "BB_LOWER": QColor("#22d3ee"),
            "SuperTrend": QColor("#f97316"),
        }
        return palette.get(name, QColor("#94a3b8"))

    def _draw_indicator_lines(self, painter: QPainter, payload: ChartPayload, view, start: int, area: QRectF, max_price: float, prange: float, step_x: float) -> None:
        line_names = ["EMA", "SMA", "VWAP", "BB_MID", "BB_UPPER", "BB_LOWER", "SuperTrend"]
        for name in line_names:
            series = payload.indicators.get(name)
            if series is None:
                continue
            painter.setPen(QPen(self._series_color(name), 1.3))
            prev = None
            for i, _ in enumerate(view):
                global_idx = start + i
                if global_idx >= len(series.values):
                    break
                value = series.values[global_idx]
                if value is None:
                    prev = None
                    continue
                x = area.left() + i * step_x + step_x / 2
                y = area.top() + ((max_price - float(value)) / prange) * area.height()
                if prev is not None:
                    painter.drawLine(int(prev[0]), int(prev[1]), int(x), int(y))
                prev = (x, y)

    def _draw_axes(self, painter: QPainter, view, price_area: QRectF, vol_area: QRectF, max_price: float, min_price: float) -> None:
        painter.setPen(QColor("#94a3b8"))
        for i in range(6):
            y = price_area.top() + (price_area.height() / 5) * i
            price = max_price - ((max_price - min_price) / 5) * i
            painter.drawText(int(price_area.right() + 8), int(y + 4), f"{price:,.2f}")

        if view:
            painter.drawText(int(price_area.left()), int(vol_area.bottom() + 18), view[0].timestamp.strftime("%d %b %H:%M"))
            painter.drawText(int(price_area.right() - 84), int(vol_area.bottom() + 18), view[-1].timestamp.strftime("%d %b %H:%M"))

    def _draw_last_price_line(self, painter: QPainter, last_price: float, area: QRectF, max_price: float, prange: float) -> None:
        y = area.top() + ((max_price - last_price) / prange) * area.height()
        painter.setPen(QPen(QColor("#f43f5e"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(int(area.left()), int(y), int(area.right()), int(y))
        painter.setPen(QColor("#fda4af"))
        painter.drawText(int(area.right() + 8), int(y + 4), f"{last_price:,.2f}")

    def _draw_ohlc_hover(self, painter: QPainter, view, area: QRectF, step_x: float) -> None:
        if self._hover_pos is None or not view:
            return
        if self._hover_pos.x() < area.left() or self._hover_pos.x() > area.right():
            return

        index = int((self._hover_pos.x() - area.left()) / max(1.0, step_x))
        index = max(0, min(len(view) - 1, index))
        candle = view[index]

        painter.setPen(QPen(QColor("#64748b"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(self._hover_pos.x(), int(area.top()), self._hover_pos.x(), int(area.bottom()))
        painter.drawLine(int(area.left()), self._hover_pos.y(), int(area.right()), self._hover_pos.y())

        text = (
            f"{candle.timestamp.strftime('%d %b %H:%M')}  "
            f"O:{candle.open:,.2f} H:{candle.high:,.2f} L:{candle.low:,.2f} C:{candle.close:,.2f} V:{candle.volume:,}"
        )
        painter.setPen(QColor("#e2e8f0"))
        painter.drawText(int(area.left()), 16, text)
        painter.drawText(self._hover_pos.x() + 8, self._hover_pos.y() - 8, f"{candle.close:,.2f}")

    def _draw_drawings(self, painter: QPainter) -> None:
        painter.setPen(QPen(QColor("#f8fafc"), 1.4))
        for drawing in self._drawings:
            self._draw_tool_shape(painter, drawing.tool, drawing.start, drawing.end)

    def _draw_preview_drawing(self, painter: QPainter) -> None:
        if self._drawing_start is None or self._drawing_preview_end is None or self._active_tool == "None":
            return
        painter.setPen(QPen(QColor("#38bdf8"), 1.2, Qt.PenStyle.DashLine))
        self._draw_tool_shape(painter, self._active_tool, self._drawing_start, self._drawing_preview_end)

    def _draw_tool_shape(self, painter: QPainter, tool: str, start: QPoint, end: QPoint) -> None:
        if tool == "Trend Line":
            painter.drawLine(start, end)
        elif tool == "Horizontal Line":
            painter.drawLine(0, start.y(), self.width(), start.y())
        elif tool == "Vertical Line":
            painter.drawLine(start.x(), 0, start.x(), self.height())
        elif tool == "Rectangle":
            rect = QRectF(start.x(), start.y(), end.x() - start.x(), end.y() - start.y()).normalized()
            painter.drawRect(rect)
        elif tool == "Text":
            painter.drawText(start, self._drawing_text_default)
        elif tool == "Arrow":
            painter.drawLine(start, end)
            dx = end.x() - start.x()
            dy = end.y() - start.y()
            if dx == 0 and dy == 0:
                return
            length = max(1.0, (dx * dx + dy * dy) ** 0.5)
            ux = dx / length
            uy = dy / length
            head = 10.0
            left = QPoint(int(end.x() - head * ux + head * 0.5 * uy), int(end.y() - head * uy - head * 0.5 * ux))
            right = QPoint(int(end.x() - head * ux - head * 0.5 * uy), int(end.y() - head * uy + head * 0.5 * ux))
            painter.drawLine(end, left)
            painter.drawLine(end, right)
