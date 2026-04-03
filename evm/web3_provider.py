"""Web3 clients using ``LegacyWebSocketProvider`` for EVM JSON-RPC."""

from __future__ import annotations

import os

from web3 import Web3


def _http_to_ws_uri(url: str) -> str:
    u = url.strip()
    if u.startswith("ws://") or u.startswith("wss://"):
        return u
    if u.startswith("https://"):
        return "wss://" + u[8:]
    if u.startswith("http://"):
        return "ws://" + u[7:]
    return u


def web3_legacy_ws(endpoint: str | None = None) -> Web3:
    """
    ``Web3(LegacyWebSocketProvider(...))``.

    ``endpoint`` defaults to ``RPC_WS_URL``, then ``RPC_URL`` (``https``/``http`` is
    rewritten to ``wss``/``ws`` on the same host).
    """
    raw = (
        endpoint
        or os.getenv("RPC_WS_URL", "").strip()
        or os.getenv("RPC_URL", "https://test.finney.opentensor.ai/")
    ).strip()
    ws_uri = _http_to_ws_uri(raw)
    return Web3(Web3.LegacyWebSocketProvider(ws_uri))
