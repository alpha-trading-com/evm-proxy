#!/usr/bin/env python3
"""
Submit SubtensorModule::add_stake_limit through DelegateProxyCaller.proxyCall (EVM).

Edit the ``add_stake_limit`` block below, then run (no CLI args).

Env (e.g. ``.env``):
  RPC_URL, PRIVATE_KEY, DELEGATE_SS58
  SUBTENSOR_CHAIN_ENDPOINT — optional; defaults to RPC_URL
"""

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
from utils.substrate_runtime_call import runtime_call_bytes

load_dotenv(os.path.join(_root, ".env"))

# ---------------------------------------------------------------------------
# add_stake_limit — edit these
# ---------------------------------------------------------------------------
HOTKEY_SS58 = ""  # validator hotkey SS58
NETUID = 1

# Set exactly one of AMOUNT_TAO or AMOUNT_RAO (or set AMOUNT_RAO via env STAKE_RAO)
AMOUNT_TAO: float | None = None
AMOUNT_RAO: int | None = None

LIMIT_PRICE = 0
ALLOW_PARTIAL = False

# Proxy precompile: name (e.g. Staking) or set PROXY_TYPE_U8 to skip name lookup
PROXY_TYPE = "Staking"
PROXY_TYPE_U8: int | None = None

GAS = 2_000_000
# None → use deployment.json contract_address
CONTRACT_ADDRESS: str | None = None
# ---------------------------------------------------------------------------


def _subtensor_from_env() -> bt.Subtensor:
    url = os.getenv("SUBTENSOR_CHAIN_ENDPOINT") or os.getenv(
        "RPC_URL", "https://test.finney.opentensor.ai/"
    )
    return bt.Subtensor(network=url)


def main() -> None:
    delegator = os.getenv("DELEGATE_SS58", "").strip()
    if not delegator:
        raise SystemExit("Set DELEGATE_SS58 in the environment")

    hotkey = HOTKEY_SS58.strip() or os.getenv("STAKE_HOTKEY", "").strip()
    if not hotkey:
        raise SystemExit("Set HOTKEY_SS58 in this script or STAKE_HOTKEY in the environment")

    netuid = int(os.getenv("STAKE_NETUID", str(NETUID)))

    amount_rao: int
    if os.getenv("STAKE_RAO"):
        amount_rao = int(os.getenv("STAKE_RAO", "0"))
    elif AMOUNT_TAO is not None:
        amount_rao = Balance.from_tao(AMOUNT_TAO).rao
    elif AMOUNT_RAO is not None:
        amount_rao = int(AMOUNT_RAO)
    else:
        raise SystemExit("Set AMOUNT_TAO or AMOUNT_RAO in this script, or STAKE_RAO in the environment")

    limit_price = int(os.getenv("STAKE_LIMIT_PRICE", str(LIMIT_PRICE)))
    allow_partial = os.getenv("STAKE_ALLOW_PARTIAL", "").lower() in (
        "1",
        "true",
        "yes",
    ) or ALLOW_PARTIAL

    contract_override = os.getenv("STAKE_CONTRACT") or CONTRACT_ADDRESS

    rpc_url = os.getenv("RPC_URL", "https://test.finney.opentensor.ai/")
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        raise SystemExit("PRIVATE_KEY is required")

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise SystemExit(f"EVM RPC failed: {rpc_url}")

    account = Account.from_key(private_key)
    if contract_override:
        contract_address = Web3.to_checksum_address(contract_override.strip())
        abi = None
    else:
        dep = load_deployment_info()
        contract_address = Web3.to_checksum_address(dep["contract_address"])
        abi = dep.get("abi")

    contract = get_contract(w3, contract_address, abi=abi)

    print("Connecting Subtensor to compose add_stake_limit …")
    subtensor = _subtensor_from_env()
    call = subtensor.substrate.compose_call(
        call_module="SubtensorModule",
        call_function="add_stake_limit",
        call_params={
            "hotkey": hotkey,
            "netuid": netuid,
            "amount_staked": int(amount_rao),
            "limit_price": limit_price,
            "allow_partial": bool(allow_partial),
        },
    )
    inner = runtime_call_bytes(call)
    pt = 0
    receipt = proxy_call_with_runtime_call(
        w3,
        account,
        contract_address,
        proxy_type=pt,
        runtime_call=inner,
        real_ss58=delegator,
        contract=contract,
    )
    p

if __name__ == "__main__":
    main()
