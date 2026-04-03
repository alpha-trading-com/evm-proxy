#!/usr/bin/env python3
"""
Submit SubtensorModule::add_stake_limit through DelegateProxyCaller.proxyCall (EVM).

Prerequisites:
  - DelegateProxyCaller deployed; real account (delegator) added the contract as a proxy
    with a proxy type compatible with staking (often `Staking`).
  - PRIVATE_KEY is the contract owner (Solidity onlyOwner).

Env:
  RPC_URL                    — EVM HTTP(S) endpoint
  PRIVATE_KEY                — Owner EVM key (signs proxyCall)
  SUBTENSOR_CHAIN_ENDPOINT   — Optional; defaults to RPC_URL (WebSocket / chain URL for metadata)

CLI:
  --delegator SS58           — Real account on whose behalf the call runs (default: DELEGATE_SS58)
  --hotkey SS58              — Validator hotkey
  --netuid N
  --tao AMOUNT               — Stake amount in TAO (mutually exclusive with --rao)
  --rao AMOUNT               — Stake amount in rao
  --limit-price P            — add_stake_limit limit_price (default 0)
  --allow-partial            — pass allow_partial=True
  --proxy-type NAME          — ProxyType name for precompile (default: Staking)
  --proxy-type-u8 N          — Override enum byte (skips name resolution)
  --contract ADDR            — Override deployment.json contract address
  --gas G                    — Gas limit (default 2_000_000)
"""

import argparse
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
from bittensor import Balance

from evm.contract import load_deployment_info
from evm.delegate_proxy import get_contract, proxy_call_with_runtime_call
from utils.proxy_type_u8 import resolve_proxy_type_u8
from utils.substrate_runtime_call import runtime_call_bytes

load_dotenv(os.path.join(_root, ".env"))


def _subtensor_from_env() -> bt.Subtensor:
    url = os.getenv("SUBTENSOR_CHAIN_ENDPOINT") or os.getenv(
        "RPC_URL", "https://test.finney.opentensor.ai/"
    )
    return bt.Subtensor(network=url)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="add_stake_limit via DelegateProxyCaller.proxyCall"
    )
    parser.add_argument(
        "--delegator",
        type=str,
        default=os.getenv("DELEGATE_SS58", "").strip() or None,
        help="Real account SS58 (default: DELEGATE_SS58)",
    )
    parser.add_argument("--hotkey", type=str, required=True)
    parser.add_argument("--netuid", type=int, required=True)
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--tao", type=float, help="Amount in TAO")
    g.add_argument("--rao", type=int, help="Amount in rao")
    parser.add_argument("--limit-price", type=int, default=0)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument(
        "--proxy-type",
        type=str,
        default="Staking",
        help="ProxyType name for forceProxyType (default: Staking)",
    )
    parser.add_argument(
        "--proxy-type-u8",
        type=int,
        default=None,
        help="Override proxy type discriminant byte",
    )
    parser.add_argument("--contract", type=str, default=None)
    parser.add_argument("--gas", type=int, default=2_000_000)

    args = parser.parse_args()

    if not args.delegator:
        parser.error("Set --delegator or DELEGATE_SS58")

    rpc_url = os.getenv("RPC_URL", "https://test.finney.opentensor.ai/")
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        raise SystemExit("PRIVATE_KEY is required")

    if args.tao is not None:
        amount_rao = Balance.from_tao(args.tao).rao
    else:
        amount_rao = int(args.rao)

    proxy_kw: int | str = (
        int(args.proxy_type_u8) if args.proxy_type_u8 is not None else args.proxy_type
    )

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

    print("Connecting Subtensor to compose add_stake_limit …")
    subtensor = _subtensor_from_env()
    try:
        call = subtensor.substrate.compose_call(
            call_module="SubtensorModule",
            call_function="add_stake_limit",
            call_params={
                "hotkey": args.hotkey,
                "netuid": args.netuid,
                "amount_staked": int(amount_rao),
                "limit_price": int(args.limit_price),
                "allow_partial": bool(args.allow_partial),
            },
        )
        inner = runtime_call_bytes(call)
        pt = resolve_proxy_type_u8(subtensor, proxy_kw)
        receipt = proxy_call_with_runtime_call(
            w3,
            account,
            contract_address,
            proxy_type=pt,
            runtime_call=inner,
            real_ss58=args.delegator,
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
