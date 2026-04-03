"""Submit Proxy pallet calls via composed extrinsics (substrate)."""

from __future__ import annotations

from typing import Any, List, Tuple

import bittensor as bt


def _unwrap_scale(value: Any) -> Any:
    while hasattr(value, "value"):
        value = value.value
    return value


def _proxy_type_and_delay_from_definition(pdef: Any) -> Tuple[str, int]:
    pdef = _unwrap_scale(pdef)
    if isinstance(pdef, dict):
        pt = pdef.get("proxy_type") or pdef.get("ProxyType")
        delay = int(pdef.get("delay", 0))
        pt = _unwrap_scale(pt)
        if isinstance(pt, str):
            return pt, delay
        if isinstance(pt, dict):
            if "name" in pt:
                return str(pt["name"]), delay
            if len(pt) == 1:
                return str(next(iter(pt.keys()))), delay
    if isinstance(pdef, (list, tuple)) and len(pdef) >= 2:
        pt, delay = pdef[0], int(pdef[1])
        pt = _unwrap_scale(pt)
        if isinstance(pt, str):
            return pt, delay
        if isinstance(pt, dict) and len(pt) == 1:
            return str(next(iter(pt.keys()))), int(delay)
    raise ValueError(f"Unsupported ProxyDefinition shape: {pdef!r}")


def list_proxies_for_principal(
    subtensor: bt.Subtensor, principal_ss58: str
) -> List[Tuple[str, str, int]]:
    """
    Return entries authorized by `principal_ss58`: (delegate_ss58, proxy_type_name, delay).
    """
    res = subtensor.substrate.query("Proxy", "Proxies", [principal_ss58])
    val = _unwrap_scale(res)
    if not val or not isinstance(val, (list, tuple)) or len(val) < 1:
        return []
    entries_raw = val[0]
    entries_raw = _unwrap_scale(entries_raw)
    if not entries_raw:
        return []
    out: List[Tuple[str, str, int]] = []
    for row in entries_raw:
        row = _unwrap_scale(row)
        if not isinstance(row, (list, tuple)) or len(row) < 2:
            continue
        delegate_acc, pdef = row[0], row[1]
        delegate_acc = _unwrap_scale(delegate_acc)
        if isinstance(delegate_acc, bytes):
            del_ss58 = subtensor.substrate.ss58_encode(delegate_acc)
        else:
            del_ss58 = str(delegate_acc)
        pt_str, delay = _proxy_type_and_delay_from_definition(pdef)
        out.append((del_ss58, pt_str, delay))
    return out


def remove_proxy_extrinsic(
    subtensor: bt.Subtensor,
    wallet: bt.Wallet,
    delegate_ss58: str,
    *,
    proxy_type: str,
    delay: int = 0,
    wait_for_inclusion: bool = True,
    wait_for_finalization: bool = False,
):
    """
    Sign and submit `Proxy::remove_proxy` as the wallet coldkey (principal / real account).

    `delegate_ss58` is the proxy account being removed (same meaning as in `add_proxy`).
    """
    call = subtensor.substrate.compose_call(
        call_module="Proxy",
        call_function="remove_proxy",
        call_params={
            "delegate": delegate_ss58,
            "proxy_type": proxy_type,
            "delay": delay,
        },
    )
    extrinsic = subtensor.substrate.create_signed_extrinsic(
        call=call,
        keypair=wallet.coldkey,
    )
    return subtensor.substrate.submit_extrinsic(
        extrinsic,
        wait_for_inclusion=wait_for_inclusion,
        wait_for_finalization=wait_for_finalization,
    )


def remove_all_proxies_for_principal(
    subtensor: bt.Subtensor,
    wallet: bt.Wallet,
    principal_ss58: str,
    *,
    wait_for_inclusion: bool = True,
    wait_for_finalization: bool = False,
) -> None:
    """Remove every proxy registered for `principal_ss58` (must match wallet coldkey)."""
    for del_ss58, pt_str, delay in list_proxies_for_principal(
        subtensor, principal_ss58
    ):
        remove_proxy_extrinsic(
            subtensor,
            wallet,
            del_ss58,
            proxy_type=pt_str,
            delay=delay,
            wait_for_inclusion=wait_for_inclusion,
            wait_for_finalization=wait_for_finalization,
        )


def add_proxy_extrinsic(
    subtensor: bt.Subtensor,
    wallet: bt.Wallet,
    delegate_ss58: str,
    *,
    proxy_type: str,
    delay: int = 0,
    wait_for_inclusion: bool = True,
    wait_for_finalization: bool = False,
):
    """
    Sign and submit `Proxy::add_proxy` as the wallet coldkey (real account).

    Returns the substrate extrinsic receipt from `submit_extrinsic`.
    """
    call = subtensor.substrate.compose_call(
        call_module="Proxy",
        call_function="add_proxy",
        call_params={
            "delegate": delegate_ss58,
            "proxy_type": proxy_type,
            "delay": delay,
        },
    )
    extrinsic = subtensor.substrate.create_signed_extrinsic(
        call=call,
        keypair=wallet.coldkey,
    )
    return subtensor.substrate.submit_extrinsic(
        extrinsic,
        wait_for_inclusion=wait_for_inclusion,
        wait_for_finalization=wait_for_finalization,
    )


if __name__ == "__main__":
    subtensor = bt.subtensor("finney")
    print(list_proxies_for_principal(subtensor, "5HCT4AarReToT1BKyLtJXJfSLs4zRS7dENnZ7iysqrqxXyV7"))