from __future__ import annotations

import json

from src.app import create_app
from src.market.websocket_client import WebSocketClient
from src.services.market_data_service import MarketDataService
from src.services.websocket_service import WebSocketService


flags = {
    "MarketDataService.start.executed": False,
    "WebSocketService.start.executed": False,
    "WebSocketClient.connect.executed": False,
    "WebSocketClient.connect.exists": hasattr(WebSocketClient, "connect"),
}

orig_mds_start = MarketDataService.start
orig_wss_start = WebSocketService.start


def patched_mds_start(self, *args, **kwargs):
    flags["MarketDataService.start.executed"] = True
    return orig_mds_start(self, *args, **kwargs)


def patched_wss_start(self, *args, **kwargs):
    flags["WebSocketService.start.executed"] = True
    return orig_wss_start(self, *args, **kwargs)


MarketDataService.start = patched_mds_start
WebSocketService.start = patched_wss_start

if hasattr(WebSocketClient, "connect"):
    orig_ws_connect = WebSocketClient.connect

    def patched_ws_connect(self, *args, **kwargs):
        flags["WebSocketClient.connect.executed"] = True
        return orig_ws_connect(self, *args, **kwargs)

    WebSocketClient.connect = patched_ws_connect

app = create_app()
app.market_data_controller.start()

result = {
    **flags,
    "should_invoke_location": (
        "src/services/market_data_service.py::MarketDataService.start (immediately after worker start)"
        if not flags["WebSocketService.start.executed"]
        else None
    ),
}
print(json.dumps(result, indent=2))
