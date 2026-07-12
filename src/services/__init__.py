__all__ = [
    "MarketDataService",
    "market_data_service",
    "MarketCache",
    "OrderService",
    "OrderValidator",
    "ValidationContext",
    "PortfolioService",
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
    if name in {"OrderValidator", "ValidationContext"}:
        from src.services.order_validator import OrderValidator, ValidationContext

        return OrderValidator if name == "OrderValidator" else ValidationContext
    if name == "PortfolioService":
        from src.services.portfolio_service import PortfolioService

        return PortfolioService
    if name == "WebSocketService":
        from src.services.websocket_service import WebSocketService

        return WebSocketService
    raise AttributeError(name)
