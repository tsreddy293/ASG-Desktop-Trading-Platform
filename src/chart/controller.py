from __future__ import annotations

from src.chart.viewmodel import ChartViewModel


class ChartController:
    """Controller that binds ChartView signals to the MVVM chart view model."""

    def __init__(self, view, viewmodel: ChartViewModel | None = None) -> None:
        self._view = view
        self._viewmodel = viewmodel or ChartViewModel()
        self._started = False

        self._view.symbol_changed.connect(self._viewmodel.set_symbol)
        self._view.timeframe_changed.connect(self._on_timeframe_changed)
        self._view.indicator_toggled.connect(self._viewmodel.set_indicator)
        self._view.chart_type_changed.connect(self._view.set_chart_type)
        self._view.drawing_tool_changed.connect(self._view.set_drawing_tool)
        self._view.clear_drawings_requested.connect(self._view.clear_drawings)
        self._view.reset_zoom_requested.connect(self._view.reset_zoom)
        self._view.auto_refresh_toggled.connect(self._viewmodel.set_auto_refresh)
        self._view.refresh_requested.connect(self._viewmodel.refresh_now)

        self._viewmodel.payload_changed.connect(self._view.render)
        self._viewmodel.status_changed.connect(self._view.set_status)

    def set_symbol(self, symbol: str, exchange: str = "NSE") -> None:
        self._viewmodel.set_symbol(symbol, exchange)
        if not self._started:
            self._viewmodel.start()
            self._started = True

    def refresh(self) -> None:
        self._viewmodel.refresh_now()

    def stop(self) -> None:
        self._viewmodel.stop()
        self._started = False

    def _on_timeframe_changed(self, timeframe: str) -> None:
        self._viewmodel.set_timeframe(timeframe)
