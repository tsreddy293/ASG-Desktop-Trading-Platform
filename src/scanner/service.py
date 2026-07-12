from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter

from src.scanner.engine import AIScannerEngine
from src.scanner.model import ScannerFilters, ScannerRow, ScannerSummary


class ScannerService:
    """Application service for AI scanner orchestration."""

    def __init__(self, engine: AIScannerEngine | None = None) -> None:
        self._engine = engine or AIScannerEngine()

    def scan(self, filters: ScannerFilters) -> tuple[list[ScannerRow], ScannerSummary]:
        start = perf_counter()
        rows, scanned_count = self._engine.run_scan(filters)
        elapsed = perf_counter() - start
        summary = ScannerSummary(
            stocks_scanned=scanned_count,
            stocks_qualified=len(rows),
            scan_time_seconds=elapsed,
            last_updated=datetime.now(timezone.utc),
        )
        return rows, summary
