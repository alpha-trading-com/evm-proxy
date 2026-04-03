"""Map ``ProxyType`` enum name to the EVM precompile ``forceProxyType`` byte (chain-specific)."""

from __future__ import annotations

from typing import Union

import bittensor as bt

from utils.substrate_runtime_call import runtime_call_bytes

_REF_DELEGATE_SS58 = "5HCT4AarReToT1BKyLtJXJfSLs4zRS7dENnZ7iysqrqxXyV7"


def resolve_proxy_type_u8(subtensor: bt.Subtensor, proxy_type: Union[int, str]) -> int:
    if isinstance(proxy_type, int):
        return int(proxy_type)
    substrate = subtensor.substrate
    name = str(proxy_type).strip()
    ref = substrate.compose_call(
        call_module="Proxy",
        call_function="add_proxy",
        call_params={
            "delegate": _REF_DELEGATE_SS58,
            "proxy_type": name,
            "delay": 0,
        },
    )
    raw = runtime_call_bytes(ref)
    pk_hex = substrate.ss58_decode(_REF_DELEGATE_SS58)
    pk = bytes.fromhex(pk_hex)
    idx = raw.find(pk)
    if idx < 0 or idx + 32 >= len(raw):
        raise RuntimeError(
            f"Could not locate delegate AccountId in encoded Proxy::add_proxy ({name!r})"
        )
    return raw[idx + 32]
