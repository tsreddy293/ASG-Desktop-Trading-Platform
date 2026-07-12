from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class WatchListEntry:
    id: int
    symbol: str
    company: str
    exchange: str
    live_price: float
    trend: str
    favorite: bool
    ai_rating: str
    risk: str


class WatchListService:
    """Business logic for the watch list manager."""

    DEFAULT_SUGGESTIONS = [
        ("SBIN", "State Bank of India"),
        ("RELIANCE", "Reliance Industries"),
        ("TCS", "Tata Consultancy Services"),
        ("INFY", "Infosys"),
        ("HDFCBANK", "HDFC Bank"),
        ("ICICIBANK", "ICICI Bank"),
        ("ITC", "ITC Limited"),
        ("LT", "Larsen & Toubro"),
        ("AXISBANK", "Axis Bank"),
        ("BAJFINANCE", "Bajaj Finance"),
    ]

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = Path(db_path or "database/asg.db")
        self._connection: sqlite3.Connection | None = None
        if str(self.db_path) == ":memory:":
            self._connection = sqlite3.connect(":memory:")
        else:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_db()

    def _connect(self) -> sqlite3.Connection:
        if self._connection is not None:
            return self._connection
        return sqlite3.connect(self.db_path)

    def _initialize_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL UNIQUE,
                    company TEXT NOT NULL,
                    exchange TEXT NOT NULL DEFAULT 'NSE',
                    live_price REAL NOT NULL DEFAULT 0.0,
                    trend TEXT NOT NULL DEFAULT 'Neutral',
                    favorite INTEGER NOT NULL DEFAULT 0,
                    ai_rating TEXT NOT NULL DEFAULT 'Neutral',
                    risk TEXT NOT NULL DEFAULT 'Medium'
                )
                """
            )
            connection.commit()
            self._ensure_schema(connection)

    def _ensure_schema(self, connection: sqlite3.Connection) -> None:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(watchlist)").fetchall()}
        if "exchange" not in columns:
            connection.execute("ALTER TABLE watchlist ADD COLUMN exchange TEXT NOT NULL DEFAULT 'NSE'")
        if "live_price" not in columns:
            connection.execute("ALTER TABLE watchlist ADD COLUMN live_price REAL NOT NULL DEFAULT 0.0")
        if "trend" not in columns:
            connection.execute("ALTER TABLE watchlist ADD COLUMN trend TEXT NOT NULL DEFAULT 'Neutral'")
        connection.commit()

    def add_symbol(self, symbol: str, company: str, exchange: str = 'NSE', live_price: float = 0.0, trend: str = 'Neutral') -> WatchListEntry:
        symbol = symbol.strip().upper()
        company = company.strip()
        exchange = exchange.strip().upper() or 'NSE'
        live_price = float(live_price)
        trend = trend.strip() or 'Neutral'
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO watchlist (symbol, company, exchange, live_price, trend) VALUES (?, ?, ?, ?, ?)",
                (symbol, company, exchange, live_price, trend),
            )
            connection.commit()
            if cursor.rowcount == 0:
                existing = self._fetch_one(connection, symbol)
                return existing
            entry_id = cursor.lastrowid
            return self._get_entry(connection, entry_id)

    def list_entries(self, favorites_only: bool = False) -> list[WatchListEntry]:
        with self._connect() as connection:
            if favorites_only:
                rows = connection.execute(
                    "SELECT id, symbol, company, exchange, live_price, trend, favorite, ai_rating, risk FROM watchlist WHERE favorite=1 ORDER BY symbol"
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT id, symbol, company, exchange, live_price, trend, favorite, ai_rating, risk FROM watchlist ORDER BY symbol"
                ).fetchall()
            return [self._row_to_entry(row) for row in rows]

    def delete_entry(self, entry_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM watchlist WHERE id = ?", (entry_id,))
            connection.commit()

    def toggle_favorite(self, entry_id: int) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE watchlist SET favorite = CASE WHEN favorite = 1 THEN 0 ELSE 1 END WHERE id = ?",
                (entry_id,),
            )
            connection.commit()

    def search(self, query: str) -> list[WatchListEntry]:
        query = query.strip().lower()
        if not query:
            return self.list_entries()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, symbol, company, exchange, live_price, trend, favorite, ai_rating, risk FROM watchlist WHERE lower(symbol) LIKE ? OR lower(company) LIKE ? ORDER BY symbol",
                (f"%{query}%", f"%{query}%"),
            ).fetchall()
            return [self._row_to_entry(row) for row in rows]

    def get_suggestions(self) -> list[str]:
        values = []
        for symbol, company in self.DEFAULT_SUGGESTIONS:
            values.append(symbol)
            values.append(company)
        return values

    def resolve_selection(self, query: str) -> tuple[str, str]:
        normalized = query.strip()
        if not normalized:
            return "", ""
        for symbol, company in self.DEFAULT_SUGGESTIONS:
            if normalized.upper() == symbol or normalized.casefold() == company.casefold():
                return symbol, company
        parts = normalized.split()
        symbol = parts[0].upper()
        company = normalized if len(parts) > 1 else normalized
        return symbol, company

    def _fetch_one(self, connection: sqlite3.Connection, symbol: str) -> WatchListEntry:
        row = connection.execute(
            "SELECT id, symbol, company, exchange, live_price, trend, favorite, ai_rating, risk FROM watchlist WHERE symbol = ?",
            (symbol,),
        ).fetchone()
        return self._row_to_entry(row)

    def _get_entry(self, connection: sqlite3.Connection, entry_id: int) -> WatchListEntry:
        row = connection.execute(
            "SELECT id, symbol, company, exchange, live_price, trend, favorite, ai_rating, risk FROM watchlist WHERE id = ?",
            (entry_id,),
        ).fetchone()
        return self._row_to_entry(row)

    @staticmethod
    def _row_to_entry(row: Optional[tuple]) -> WatchListEntry:
        if row is None:
            raise ValueError("Entry not found")
        return WatchListEntry(
            id=row[0],
            symbol=row[1],
            company=row[2],
            exchange=row[3],
            live_price=float(row[4]),
            trend=row[5],
            favorite=bool(row[6]),
            ai_rating=row[7],
            risk=row[8],
        )
