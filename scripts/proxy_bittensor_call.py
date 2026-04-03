#!/usr/bin/env python3
"""
Run any Bittensor pallet call through DelegateProxyCaller (EVM proxy precompile).

Either:

1) Compose from metadata (any call supported by ``substrate.compose_call``)::

    ./venv/bin/python scripts/proxy_bittensor_call.py \\
      --module SubtensorModule \\
      --function remove_stake_limit \\
      --params-json '{"hotkey":"5...","netuid":1,"amount_unstaked":1000000,"limit_price":0,"allow_partial":false}'

2) Or pass pre-encoded RuntimeCall hex (no Subtensor compose step)::

    ./venv/bin/python scripts/proxy_bittensor_call.py --call-hex 0x.... --proxy-type-u8 8

Env: RPC_URL, PRIVATE_KEY, SUBTENSOR_CHAIN_ENDPOINT (optional), DELEGATE_SS58 (if --delegator omitted).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_script_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_script_dir)
if _root not in sys.path:
    sys.path.insert(0, _root)

from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

import bittensor as bt

from evm.bittensor_proxy import (
    bittensor_call_via_proxy_contract,
    runtime_call_via_proxy_contract,
)
from evm.contract import load_deployment_info
from evm.delegate_proxy import get_contract

load_dotenv(os.path.join(_root, ".env"))


def _subtensor_from_env() -> bt.Subtensor:
    url = os.getenv("SUBTENSOR_CHAIN_ENDPOINT") or os.getenv(
        "RPC_URL", "https://test.finney.opentensor.ai/"
    )
    return bt.Subtensor(network=url)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generic Bittensor call via DelegateProxyCaller.proxyCall"
    )
    parser.add_argument(
        "--call-hex",
        type=str,
        default=None,
        help="Pre-encoded SCALE RuntimeCall (0x-prefixed hex); use with --proxy-type-u8",
    )
    parser.add_argument(
        "--module",
        type=str,
        default=None,
        help="Pallet name for compose_call, e.g. SubtensorModule",
    )
    parser.add_argument(
        "--function",
        type=str,
        default=None,
        help="Call function name, e.g. remove_stake_limit",
    )
    parser.add_argument(
        "--params-json",
        type=str,
        default=None,
        help="JSON object of call_params for compose_call",
    )
    parser.add_argument(
        "--params-file",
        type=str,
        default=None,
        help="Path to JSON file (alternative to --params-json)",
    )

    parser.add_argument(
        "--delegator",
        type=str,
        default=os.getenv("DELEGATE_SS58", "").strip() or None,
        help="Real account SS58 (default: DELEGATE_SS58)",
    )
    parser.add_argument(
        "--proxy-type",
        type=str,
        default="Staking",
        help="ProxyType name when using string proxy type (compose path only)",
    )
    parser.add_argument(
        "--proxy-type-u8",
        type=int,
        default=None,
        help="Override ProxyType byte for precompile (required with --call-hex if not using name)",
    )
    parser.add_argument("--contract", type=str, default=None)
    parser.add_argument("--gas", type=int, default=2_000_000)

    args = parser.parse_args()

    use_hex = bool(args.call_hex)
    use_compose = bool(args.module or args.function or args.params_json or args.params_file)

    if use_hex == use_compose:
        parser.error(
            "Use exactly one mode: either --call-hex (pre-encoded call), "
            "or --module + --function + (--params-json | --params-file)"
        )

    if use_hex:
        params = None
        if args.proxy_type_u8 is None:
            parser.error(
                "--call-hex requires --proxy-type-u8 (no Subtensor connection to resolve type names)"
            )
    else:
        if not args.module or not args.function:
            parser.error("Compose mode requires --module and --function")
        if args.params_json is None and args.params_file is None:
            parser.error("Compose mode requires --params-json or --params-file")
        if args.params_file:
            with open(args.params_file, "r", encoding="utf-8") as f:
                params = json.load(f)
        else:
            params = json.loads(args.params_json)
        if not isinstance(params, dict):
            parser.error("params must be a JSON object")

    if not args.delegator:
        parser.error("Set --delegator or DELEGATE_SS58")

    rpc_url = os.getenv("RPC_URL", "https://test.finney.opentensor.ai/")
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        raise SystemExit("PRIVATE_KEY is required")

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise SystemExit(f"EVM RPC failed: {rpc_url}")

    account = Account.from_key(private_key)
    if args.contract:
        contract_address = Web3.to_checksum_address(args.contract)
        abi = None
    else:
        dep = load_deployment_info()
        contract_address = Web3.to_checksum_address(dep["contract_address"])
        abi = dep.get("abi")

    contract = get_contract(w3, contract_address, abi=abi)

    if args.call_hex is not None:
        receipt = runtime_call_via_proxy_contract(
            w3,
            account,
            contract_address,
            delegator_ss58=args.delegator,
            proxy_type_u8=int(args.proxy_type_u8),
            runtime_call=args.call_hex,
            gas=args.gas,
            contract=contract,
            verbose=True,
        )
    else:
        subtensor = _subtensor_from_env()
        try:
            proxy_kw: int | str
            if args.proxy_type_u8 is not None:
                proxy_kw = int(args.proxy_type_u8)
            else:
                proxy_kw = args.proxy_type
            receipt = bittensor_call_via_proxy_contract(
                subtensor,
                w3,
                account,
                contract_address,
                delegator_ss58=args.delegator,
                proxy_type=proxy_kw,
                call_module=args.module,
                call_function=args.function,
                call_params=params,
                gas=args.gas,
                contract=contract,
                verbose=True,
            )
        finally:
            subtensor.close()

    if receipt.status != 1:
        raise SystemExit("Transaction reverted")


if __name__ == "__main__":
    main()
