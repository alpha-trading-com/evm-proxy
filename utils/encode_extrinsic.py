"""
Compose SCALE-encoded `RuntimeCall` bytes for Bittensor / Subtensor extrinsics.

Used with DelegateProxyCaller.proxyCall (EVM): pass the raw call bytes the
precompile forwards to `Proxy::proxy` on behalf of the real account.
"""

from __future__ import annotations

from typing import Any

import bittensor as bt


def _call_data_bytes(call: Any) -> bytes:
    """Extract raw encoded call from substrate `compose_call` result."""
    scale_data = call.data
    raw = getattr(scale_data, "data", None)
    if raw is None or not isinstance(raw, (bytes, bytearray)):
        raise RuntimeError(
            "Could not read composed call bytes (ScaleBytes format may have changed)"
        )
    return bytes(raw)


def proxy_type_u8_from_name(subtensor: bt.Subtensor, proxy_type_name: str) -> int:
    """
    Discriminant byte for `ProxyType` as used by the EVM precompile `forceProxyType`.

    Resolved by composing `Proxy::add_proxy` with the same type name and locating
    the delegate AccountId32 in the encoded payload; the following byte is the enum index.
    """
    # Any valid SS58 AccountId32 works; only encoding layout is used.
    placeholder = "5HCT4AarReToT1BKyLtJXJfSLs4zRS7dENnZ7iysqrqxXyV7"
    call = subtensor.substrate.compose_call(
        call_module="Proxy",
        call_function="add_proxy",
        call_params={
            "delegate": placeholder,
            "proxy_type": proxy_type_name.strip(),
            "delay": 0,
        },
    )
    raw = _call_data_bytes(call)
    pk_hex = subtensor.substrate.ss58_decode(placeholder)
    pk = bytes.fromhex(pk_hex)
    idx = raw.find(pk)
    if idx < 0 or idx + 32 >= len(raw):
        raise RuntimeError(
            f"Could not locate delegate account id in encoded Proxy::add_proxy ({proxy_type_name!r})"
        )
    return raw[idx + 32]


def encode_add_stake_limit_call(
    subtensor: bt.Subtensor,
    hotkey_ss58: str,
    netuid: int,
    amount_staked_rao: int,
    limit_price: int,
    allow_partial: bool = False,
) -> bytes:
    """
    SCALE-encoded `SubtensorModule::add_stake_limit` call (pallet index + call index + args).

    Pass these bytes to DelegateProxyCaller.proxyCall as `call`.
    """
    call = subtensor.substrate.compose_call(
        call_module="SubtensorModule",
        call_function="add_stake_limit",
        call_params={
            "hotkey": hotkey_ss58,
            "netuid": netuid,
            "amount_staked": int(amount_staked_rao),
            "limit_price": int(limit_price),
            "allow_partial": bool(allow_partial),
        },
    )
    return _call_data_bytes(call)


def encode_add_stake_limit_call_hex(
    subtensor: bt.Subtensor,
    hotkey_ss58: str,
    netuid: int,
    amount_staked_rao: int,
    limit_price: int,
    allow_partial: bool = False,
    *,
    prefix_0x: bool = True,
) -> str:
    """Same as `encode_add_stake_limit_call`, returns hex string for web3 / CLI."""
    h = encode_add_stake_limit_call(
        subtensor,
        hotkey_ss58,
        netuid,
        amount_staked_rao,
        limit_price,
        allow_partial,
    ).hex()
    return ("0x" + h) if prefix_0x else h
