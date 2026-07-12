"""Scanner package."""

from src.scanner.controller import ScannerController
from src.scanner.engine import AIScannerEngine
from src.scanner.model import ScannerFilters, ScannerRow, ScannerSummary
from src.scanner.service import ScannerService


class ScannerModel:
	"""Compatibility wrapper for Scanner model naming."""

	Filters = ScannerFilters
	Row = ScannerRow
	Summary = ScannerSummary


__all__ = [
	"AIScannerEngine",
	"ScannerService",
	"ScannerModel",
	"ScannerController",
	"ScannerFilters",
	"ScannerRow",
	"ScannerSummary",
]
