#!/usr/bin/env python3
"""
Submit SubtensorModule::add_stake_limit through DelegateProxyCaller.proxyCall (EVM).

Edit the example ``add_stake_limit`` inputs below, then run (no CLI args).

Env (``.env``): RPC_URL or RPC_WS_URL (WebSocket for EVM), PRIVATE_KEY, DELEGATE_SS58;
optional SUBTENSOR_CHAIN_ENDPOINT.
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
from evm.web3_provider import web3_legacy_ws
from utils.substrate_runtime_call import runtime_call_bytes

load_dotenv(os.path.join(_root, ".env"))



def _subtensor_from_env() -> bt.Subtensor:
    url = os.getenv("SUBTENSOR_CHAIN_ENDPOINT") or os.getenv(
        "RPC_URL", "https://test.finney.opentensor.ai/"
    )
    return bt.Subtensor(network=url)


def main() -> None:
    delegator = os.getenv("DELEGATE_SS58", "").strip()
    if not delegator:
        raise SystemExit("Set DELEGATE_SS58 in the environment")
    rpc_url = os.getenv("RPC_URL", "https://test.finney.opentensor.ai/")
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        raise SystemExit("PRIVATE_KEY is required")

    w3 = web3_legacy_ws(rpc_url)
    if not w3.is_connected():
        raise SystemExit(f"EVM WebSocket connection failed for {rpc_url!r}")

    account = Account.from_key(private_key)
    dep = load_deployment_info()
    contract_address = Web3.to_checksum_address(dep["contract_address"])
    abi = dep.get("abi")

    contract = get_contract(w3, contract_address, abi=abi)

    print("Connecting Subtensor to compose add_stake_limit …")
    subtensor = _subtensor_from_env()
    try:
        # -------------------------------------------------------------------------
        # add_stake_limit inputs (example — replace with your values)
        # ---------------------------------------------------------------------------
        HOTKEY_SS58 = "5E2LP6EnZ54m3wS8s1yPvD5c3xo71kQroBw7aUVK32TKeZ5u"
        NETUID = 64
        AMOUNT_TAO = 0.1  # stake size; or set AMOUNT_RAO and AMOUNT_TAO = None
        AMOUNT_RAO = Balance.from_tao(1.00).rao
        LIMIT_PRICE = Balance.from_tao(0.2).rao
        ALLOW_PARTIAL = False

        # ---------------------------------------------------------------------------
        call = subtensor.substrate.compose_call(
            call_module="SubtensorModule",
            call_function="remove_stake",
            call_params={
                "hotkey": HOTKEY_SS58,
                "netuid": NETUID,
                "amount_unstaked": int(AMOUNT_RAO or 0),
            },
        )
        inner = runtime_call_bytes(call)
        receipt = proxy_call_with_runtime_call(
            w3,
            account,
            contract_address,
            proxy_type=0,
            runtime_call=inner,
            real_ss58=delegator,
            contract=contract,
        )
    finally:
        subtensor.close()
    if receipt.status != 1:
        raise SystemExit("Transaction reverted")


if __name__ == "__main__":
    main()
