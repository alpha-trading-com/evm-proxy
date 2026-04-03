"""
Proxy Substrate calls through DelegateProxyCaller (EVM).

- :func:`evm.delegate_proxy.proxy_call_with_runtime_call` — inner call already encoded
- :func:`evm.bittensor_proxy.bittensor_call_via_proxy_contract` — compose via ``substrate.compose_call`` then proxy
"""

from evm.bittensor_proxy import (
    bittensor_call_via_proxy_contract,
    resolve_proxy_type_u8,
    runtime_call_via_proxy_contract,
)
from evm.delegate_proxy import get_contract, proxy_call, proxy_call_with_runtime_call
from utils.substrate_runtime_call import runtime_call_bytes

__all__ = [
    "proxy_call",
    "proxy_call_with_runtime_call",
    "runtime_call_bytes",
    "bittensor_call_via_proxy_contract",
    "runtime_call_via_proxy_contract",
    "resolve_proxy_type_u8",
    "get_contract",
]
