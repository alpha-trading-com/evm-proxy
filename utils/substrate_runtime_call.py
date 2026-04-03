"""
Normalize SCALE-encoded ``RuntimeCall`` bytes (from ``substrate.compose_call`` or hex).

Call ``substrate.compose_call(...)`` yourself, then ``runtime_call_bytes(call)`` for the precompile payload.
"""

from __future__ import annotations

from typing import Any

__all__ = ["runtime_call_bytes"]


def _encoded_call_from_compose_result(call: Any) -> bytes:
    scale_data = call.data
    raw = getattr(scale_data, "data", None)
    if raw is None or not isinstance(raw, (bytes, bytearray)):
        raise RuntimeError(
            "Could not read bytes from composed call (ScaleBytes layout may have changed)"
        )
    return bytes(raw)


def runtime_call_bytes(call: Any) -> bytes:
    """
    Normalize to raw SCALE ``RuntimeCall`` bytes.

    Accepts:

    - ``bytes`` / ``bytearray``
    - hex ``str`` (optional ``0x``)
    - return value of ``substrate.compose_call(...)`` (object with ``.data``)
    """
    if isinstance(call, (bytes, bytearray)):
        return bytes(call)
    if isinstance(call, str):
        h = call.strip()
        if h.startswith(("0x", "0X")):
            h = h[2:]
        if len(h) % 2 != 0:
            raise ValueError("Runtime call hex string must have even length")
        return bytes.fromhex(h)
    return _encoded_call_from_compose_result(call)
