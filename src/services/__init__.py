__all__ = [
    "MarketDataService",
    "market_data_service",
    "MarketCache",
    "OrderService",
    "WebSocketService",
]


def __getattr__(name: str):
    if name in {"MarketDataService", "market_data_service"}:
        from src.services.market_data_service import MarketDataService, market_data_service

        return MarketDataService if name == "MarketDataService" else market_data_service
    if name == "MarketCache":
        from src.services.market_cache import MarketCache

        return MarketCache
    if name == "OrderService":
        from src.services.order_service import OrderService

        return OrderService
    if name == "WebSocketService":
        from src.services.websocket_service import WebSocketService

        return WebSocketService
    raise AttributeError(name)
