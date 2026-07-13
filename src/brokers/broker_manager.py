from __future__ import annotations

import inspect
import threading
import traceback
from datetime import datetime, timezone
from typing import Any

from src.brokers.angelone import AngelOneBroker
from src.brokers.base_broker import BaseBroker, BrokerConnectionError
from src.brokers.fivepaisa import FivePaisaLoginService, FivePaisaMarketService, FivePaisaOrderService, FivePaisaPortfolioService
from src.brokers.upstox import UpstoxBroker
from src.brokers.zerodha import ZerodhaBroker
from src.core.config import config
from src.core.logger import app_logger


class FivePaisaBroker(BaseBroker):
    name = "fivepaisa"

    def __init__(self) -> None:
        self._login_service = FivePaisaLoginService()
        self._market = FivePaisaMarketService(self._login_service)
        self._orders = FivePaisaOrderService(self._login_service)
        self._portfolio = FivePaisaPortfolioService(self._login_service)

    def login(self) -> None:
        self._login_service.login()

    def logout(self) -> None:
        self._login_service.logout()

    def is_logged_in(self) -> bool:
        return self._login_service.is_logged_in()

    def get_profile(self) -> dict[str, Any]:
        return self._portfolio.get_profile()

    def get_quote(self, symbol: str, **kwargs) -> dict[str, Any]:
        return self._market.get_quote(symbol, **kwargs)

    def get_quotes(self, symbols: list[str] | None = None, **kwargs) -> list[dict[str, Any]]:
        return self._market.get_quotes(symbols, **kwargs)

    def get_option_chain(self, symbol: str, **kwargs) -> dict[str, Any]:
        return self._market.get_option_chain(symbol, **kwargs)

    def get_market_depth(self, symbol: str, **kwargs) -> dict[str, Any]:
        return self._market.get_market_depth(symbol, **kwargs)

    def get_historical_data(self, symbol: str, **kwargs) -> list[dict[str, Any]]:
        return self._market.get_historical_data(symbol, **kwargs)

    def place_order(self, **kwargs) -> dict[str, Any]:
        return self._orders.place_order(**kwargs)

    def modify_order(self, **kwargs) -> dict[str, Any]:
        return self._orders.modify_order(**kwargs)

    def cancel_order(self, **kwargs) -> dict[str, Any]:
        return self._orders.cancel_order(**kwargs)

    def get_order_book(self, **kwargs) -> list[dict[str, Any]]:
        return self._orders.get_order_book(**kwargs)

    def get_trade_book(self, **kwargs) -> list[dict[str, Any]]:
        return self._orders.get_trade_book(**kwargs)

    def get_positions(self, **kwargs) -> list[dict[str, Any]]:
        return self._portfolio.get_positions(**kwargs)

    def get_holdings(self, **kwargs) -> list[dict[str, Any]]:
        return self._portfolio.get_holdings(**kwargs)

    def get_funds(self, **kwargs) -> dict[str, Any]:
        return self._portfolio.get_funds(**kwargs)


class UnavailableBroker(BaseBroker):
    def __init__(self, name: str) -> None:
        self.name = name

    def login(self) -> None:
        raise BrokerConnectionError("Broker connection unavailable.")

    def logout(self) -> None:
        return None

    def is_logged_in(self) -> bool:
        return False

    def get_profile(self) -> dict[str, Any]:
        raise BrokerConnectionError("Broker connection unavailable.")

    def get_quote(self, symbol: str, **kwargs) -> dict[str, Any]:
        raise BrokerConnectionError("Broker connection unavailable.")

    def get_quotes(self, symbols: list[str] | None = None, **kwargs) -> list[dict[str, Any]]:
        raise BrokerConnectionError("Broker connection unavailable.")

    def get_option_chain(self, symbol: str, **kwargs) -> dict[str, Any]:
        raise BrokerConnectionError("Broker connection unavailable.")

    def get_market_depth(self, symbol: str, **kwargs) -> dict[str, Any]:
        raise BrokerConnectionError("Broker connection unavailable.")

    def get_historical_data(self, symbol: str, **kwargs) -> list[dict[str, Any]]:
        raise BrokerConnectionError("Broker connection unavailable.")

    def place_order(self, **kwargs) -> dict[str, Any]:
        raise BrokerConnectionError("Broker connection unavailable.")

    def modify_order(self, **kwargs) -> dict[str, Any]:
        raise BrokerConnectionError("Broker connection unavailable.")

    def cancel_order(self, **kwargs) -> dict[str, Any]:
        raise BrokerConnectionError("Broker connection unavailable.")

    def get_order_book(self, **kwargs) -> list[dict[str, Any]]:
        raise BrokerConnectionError("Broker connection unavailable.")

    def get_trade_book(self, **kwargs) -> list[dict[str, Any]]:
        raise BrokerConnectionError("Broker connection unavailable.")

    def get_positions(self, **kwargs) -> list[dict[str, Any]]:
        raise BrokerConnectionError("Broker connection unavailable.")

    def get_holdings(self, **kwargs) -> list[dict[str, Any]]:
        raise BrokerConnectionError("Broker connection unavailable.")

    def get_funds(self, **kwargs) -> dict[str, Any]:
        raise BrokerConnectionError("Broker connection unavailable.")


class BrokerManager:
    """Routes all broker calls to the active broker implementation."""

    _login_trace_lock = threading.Lock()

    def __init__(self) -> None:
        self._brokers: dict[str, BaseBroker] = {
            "fivepaisa": FivePaisaBroker(),
            "angelone": AngelOneBroker(),
            "zerodha": ZerodhaBroker(),
            "upstox": UpstoxBroker(),
            "dhan": UnavailableBroker("dhan"),
            "aliceblue": UnavailableBroker("aliceblue"),
            "fyers": UnavailableBroker("fyers"),
        }
        self._active_name = str(config.get("default_broker", "fivepaisa") or "fivepaisa").strip().lower()
        if self._active_name not in self._brokers:
            self._active_name = "fivepaisa"

    def set_active_broker(self, broker_name: str) -> None:
        name = (broker_name or "").strip().lower()
        if name not in self._brokers:
            raise BrokerConnectionError("Broker connection unavailable.")
        self._active_name = name
        config.set("default_broker", name)
        app_logger.info(f"Active broker switched to {name}")

    def active_broker_name(self) -> str:
        return self._active_name

    def active_broker(self) -> BaseBroker:
        return self._brokers[self._active_name]

    def _safe_call(self, method_name: str, *args, **kwargs):
        broker = self.active_broker()
        method = getattr(broker, method_name)
        try:
            return method(*args, **kwargs)
        except BrokerConnectionError:
            app_logger.warning(f"Broker connection unavailable for {broker.name}.{method_name}")
            raise
        except Exception as exc:
            app_logger.error(f"Broker error in {broker.name}.{method_name}: {exc}")
            raise BrokerConnectionError("Broker connection unavailable.") from exc

    def login(self) -> None:
        # Compatibility alias; explicit connect is the canonical auth trigger.
        self.connect()

    def connect(self) -> None:
        stack = inspect.stack(context=0)
        frame = stack[1] if len(stack) > 1 else stack[0]
        with self._login_trace_lock:
            current = getattr(self, "_login_call_sequence", 0) + 1
            self._login_call_sequence = current
        app_logger.info(
            f"AUTH_PROBE event=BrokerManager.connect seq={current} ts={datetime.now(timezone.utc).isoformat()} "
            f"thread={threading.current_thread().name} caller_file={frame.filename} caller_line={frame.lineno}\n"
            f"{''.join(traceback.format_stack(limit=10))}"
        )
        self._safe_call("login")

    def logout(self) -> None:
        self._safe_call("logout")

    def is_logged_in(self) -> bool:
        return bool(self._safe_call("is_logged_in"))

    def get_profile(self) -> dict[str, Any]:
        return self._safe_call("get_profile")

    def get_quote(self, symbol: str, **kwargs) -> dict[str, Any]:
        return self._safe_call("get_quote", symbol, **kwargs)

    def get_quotes(self, symbols: list[str] | None = None, **kwargs) -> list[dict[str, Any]]:
        return self._safe_call("get_quotes", symbols, **kwargs)

    def get_option_chain(self, symbol: str, **kwargs) -> dict[str, Any]:
        return self._safe_call("get_option_chain", symbol, **kwargs)

    def get_market_depth(self, symbol: str, **kwargs) -> dict[str, Any]:
        return self._safe_call("get_market_depth", symbol, **kwargs)

    def get_historical_data(self, symbol: str, **kwargs) -> list[dict[str, Any]]:
        return self._safe_call("get_historical_data", symbol, **kwargs)

    def place_order(self, **kwargs) -> dict[str, Any]:
        return self._safe_call("place_order", **kwargs)

    def modify_order(self, **kwargs) -> dict[str, Any]:
        return self._safe_call("modify_order", **kwargs)

    def cancel_order(self, **kwargs) -> dict[str, Any]:
        return self._safe_call("cancel_order", **kwargs)

    def get_order_book(self, **kwargs) -> list[dict[str, Any]]:
        return self._safe_call("get_order_book", **kwargs)

    def get_trade_book(self, **kwargs) -> list[dict[str, Any]]:
        return self._safe_call("get_trade_book", **kwargs)

    def get_positions(self, **kwargs) -> list[dict[str, Any]]:
        return self._safe_call("get_positions", **kwargs)

    def get_holdings(self, **kwargs) -> list[dict[str, Any]]:
        return self._safe_call("get_holdings", **kwargs)

    def get_funds(self, **kwargs) -> dict[str, Any]:
        return self._safe_call("get_funds", **kwargs)


broker_manager = BrokerManager()
