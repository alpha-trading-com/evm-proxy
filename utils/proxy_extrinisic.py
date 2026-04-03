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


def _delegate_field_to_bytes(delegate_field: Any) -> bytes:
    """AccountId32 from storage: bytes, or nested tuples of ints (scalecodec)."""
    d = _unwrap_scale(delegate_field)
    if isinstance(d, bytes):
        if len(d) != 32:
            raise ValueError(f"AccountId must be 32 bytes, got {len(d)}")
        return d
    while isinstance(d, (list, tuple)) and len(d) == 1:
        d = _unwrap_scale(d[0])
    if isinstance(d, (list, tuple)):
        ints: List[int] = []
        for x in d:
            x = _unwrap_scale(x)
            if isinstance(x, int):
                ints.append(x)
            elif isinstance(x, (list, tuple)):
                for y in x:
                    y = _unwrap_scale(y)
                    if isinstance(y, int):
                        ints.append(y)
        if len(ints) == 32:
            return bytes(ints)
    raise ValueError(f"Cannot decode delegate AccountId: {delegate_field!r}")


def _collect_proxy_definition_dicts(obj: Any, out: List[Any]) -> None:
    """Find ProxyDefinition structs encoded as dicts with 'delegate' + 'proxy_type'."""
    obj = _unwrap_scale(obj)
    if isinstance(obj, dict) and "delegate" in obj:
        pt = obj.get("proxy_type") or obj.get("ProxyType")
        if pt is not None:
            out.append(obj)
            return
    if isinstance(obj, (list, tuple)):
        for x in obj:
            _collect_proxy_definition_dicts(x, out)


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
    entries_blob = _unwrap_scale(val[0])
    if not entries_blob:
        return []

    struct_rows: List[Any] = []
    _collect_proxy_definition_dicts(entries_blob, struct_rows)

    out: List[Tuple[str, str, int]] = []
    if struct_rows:
        for row in struct_rows:
            row = _unwrap_scale(row)
            acc = _delegate_field_to_bytes(row["delegate"])
            del_ss58 = subtensor.substrate.ss58_encode(acc)
            pt_str, delay = _proxy_type_and_delay_from_definition(row)
            out.append((del_ss58, pt_str, delay))
        return out

    # Legacy: Vec<(AccountId, ProxyDefinition)>
    for row in entries_blob:
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