from src.brokers.base_broker import BaseBroker, BrokerConnectionError


class UpstoxBroker(BaseBroker):
    name = "upstox"

    def login(self) -> None:
        raise BrokerConnectionError("Broker connection unavailable.")

    def logout(self) -> None:
        return None

    def is_logged_in(self) -> bool:
        return False

    def get_profile(self):
        raise BrokerConnectionError("Broker connection unavailable.")

    def get_quote(self, symbol: str, **kwargs):
        raise BrokerConnectionError("Broker connection unavailable.")

    def get_quotes(self, symbols=None, **kwargs):
        raise BrokerConnectionError("Broker connection unavailable.")

    def get_option_chain(self, symbol: str, **kwargs):
        raise BrokerConnectionError("Broker connection unavailable.")

    def get_market_depth(self, symbol: str, **kwargs):
        raise BrokerConnectionError("Broker connection unavailable.")

    def get_historical_data(self, symbol: str, **kwargs):
        raise BrokerConnectionError("Broker connection unavailable.")

    def place_order(self, **kwargs):
        raise BrokerConnectionError("Broker connection unavailable.")

    def modify_order(self, **kwargs):
        raise BrokerConnectionError("Broker connection unavailable.")

    def cancel_order(self, **kwargs):
        raise BrokerConnectionError("Broker connection unavailable.")

    def get_order_book(self, **kwargs):
        raise BrokerConnectionError("Broker connection unavailable.")

    def get_trade_book(self, **kwargs):
        raise BrokerConnectionError("Broker connection unavailable.")

    def get_positions(self, **kwargs):
        raise BrokerConnectionError("Broker connection unavailable.")

    def get_holdings(self, **kwargs):
        raise BrokerConnectionError("Broker connection unavailable.")

    def get_funds(self, **kwargs):
        raise BrokerConnectionError("Broker connection unavailable.")
