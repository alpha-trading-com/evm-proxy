"""
Proxy Substrate calls through DelegateProxyCaller (EVM).

- :func:`evm.delegate_proxy.proxy_call_with_runtime_call` — submit ``proxyCall`` (owner signs)
- :func:`resolve_proxy_type_u8` — map ``ProxyType`` name to precompile u8 for this chain
- :func:`runtime_call_via_proxy_contract` — thin alias of ``proxy_call_with_runtime_call``
"""

from __future__ import annotations

from typing import Any, Union

import bittensor as bt
from eth_account import Account
from web3 import Web3
from web3.types import TxReceipt

from evm.delegate_proxy import get_contract, proxy_call_with_runtime_call
from utils.substrate_runtime_call import runtime_call_bytes

_PROXY_TYPE_REF_DELEGATE = "5HCT4AarReToT1BKyLtJXJfSLs4zRS7dENnZ7iysqrqxXyV7"


def resolve_proxy_type_u8(
    subtensor: bt.Subtensor, proxy_type: Union[int, str]
) -> int:
    if isinstance(proxy_type, int):
        return int(proxy_type)
    substrate = subtensor.substrate
    name = str(proxy_type).strip()
    ref = substrate.compose_call(
        call_module="Proxy",
        call_function="add_proxy",
        call_params={
            "delegate": _PROXY_TYPE_REF_DELEGATE,
            "proxy_type": name,
            "delay": 0,
        },
    )
    raw = runtime_call_bytes(ref)
    pk_hex = substrate.ss58_decode(_PROXY_TYPE_REF_DELEGATE)
    pk = bytes.fromhex(pk_hex)
    idx = raw.find(pk)
    if idx < 0 or idx + 32 >= len(raw):
        raise RuntimeError(
            f"Could not locate delegate AccountId in encoded Proxy::add_proxy ({name!r})"
        )
    return raw[idx + 32]


def runtime_call_via_proxy_contract(
    w3: Web3,
    owner_account: Account,
    contract_address: str,
    *,
    delegator_ss58: str,
    proxy_type_u8: int,
    runtime_call: Any,
    gas: int = 2_000_000,
    contract=None,
    verbose: bool = True,
) -> TxReceipt:
    """Pre-encoded inner call + contract ``proxyCall`` (alias of :func:`proxy_call_with_runtime_call`)."""
    return proxy_call_with_runtime_call(
        w3,
        owner_account,
        contract_address,
        proxy_type=int(proxy_type_u8),
        runtime_call=runtime_call,
        delegator_ss58=delegator_ss58.strip(),
        gas=gas,
        contract=contract,
        verbose=verbose,
    )


__all__ = [
    "proxy_call_with_runtime_call",
    "runtime_call_bytes",
    "runtime_call_via_proxy_contract",
    "resolve_proxy_type_u8",
    "get_contract",
]
