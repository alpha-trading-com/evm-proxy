#!/usr/bin/env python3
"""
Deploy DelegateProxyCaller (EVM), then set that contract's SS58 as the only Proxy delegate
for DELEGATE_SS58 (Substrate principal).

Steps:
1. Connect to Subtensor (same chain as RPC_URL / SUBTENSOR_CHAIN_ENDPOINT).
2. Remove all existing proxies for DELEGATE_SS58 (signed by that account's coldkey).
3. Deploy the contract with PRIVATE_KEY (EVM deployer).
4. Add proxy: principal = DELEGATE_SS58, delegate = contract SS58 (Blake2 evm: + H160).

Env (see .env):
  RPC_URL / RPC_WS_URL     — EVM endpoint; Web3 uses LegacyWebSocketProvider (``wss://``; ``https`` URLs are rewritten).
  PRIVATE_KEY              — Secp256k1 hex for contract deployment.
  DELEGATE_SS58            — Principal SS58 whose Proxy entries are cleared/replaced.

  SUBTENSOR_CHAIN_ENDPOINT — Optional; defaults to RPC_URL. Substrate uses WebSocket
                             (https is rewritten to wss); use a node that exposes WS.

  DELEGATE_COLDKEY_MNEMONIC | DELEGATE_COLDKEY_SEED_HEX | DELEGATE_COLDKEY_URI
                            — One required unless using a file wallet below.
  BT_WALLET_NAME, BT_WALLET_HOTKEY, WALLET_PASSWORD — File wallet for DELEGATE_SS58 coldkey.

  PROXY_TYPE               — Optional; default Any (matches EVM precompile usage).
  PROXY_DELAY              — Optional; default 0.
"""

import importlib.util
import json
import os
import sys

from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

import bittensor as bt
from bittensor_wallet.keypair import Keypair as BtKeypair
from eth_account import Account
from web3 import Web3

from evm.address import h160_to_ss58
from evm.web3_provider import web3_legacy_ws
from utils.proxy_extrinisic import (
    add_proxy_extrinsic,
    remove_all_proxies_for_principal,
)


def _load_deploy_module():
    path = os.path.join(PROJECT_ROOT, "scripts", "deploy.py")
    spec = importlib.util.spec_from_file_location("evm_deploy_script", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    delegate_ss58 = os.getenv("DELEGATE_SS58")
    if not delegate_ss58 or not delegate_ss58.strip():
        raise ValueError("DELEGATE_SS58 is required")

    rpc_evm = os.getenv("RPC_URL", "https://test.finney.opentensor.ai/")
    subtensor_url = os.getenv("SUBTENSOR_CHAIN_ENDPOINT") or rpc_evm

    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        raise ValueError("PRIVATE_KEY is required for EVM deployment")

    proxy_type = os.getenv("PROXY_TYPE", "Any").strip()
    proxy_delay = int(os.getenv("PROXY_DELAY", "0"))

    print(f"Connecting Subtensor to {subtensor_url!r} …")
    subtensor = bt.Subtensor(network=subtensor_url)
    wallet = bt.Wallet(name=os.getenv("DELEGATE_WALLET_NAME"))
    wallet.unlock_coldkey()

    print(f"Principal (DELEGATE_SS58): {delegate_ss58.strip()}")
    print("Removing existing proxies …")
    remove_all_proxies_for_principal(
        subtensor,
        wallet,
        delegate_ss58.strip(),
        wait_for_inclusion=True,
        wait_for_finalization=False,
    )

    deploy_mod = _load_deploy_module()
    w3 = web3_legacy_ws(rpc_evm)
    if not w3.is_connected():
        raise ConnectionError(f"EVM: failed to connect (WebSocket) for {rpc_evm!r}")

    account = Account.from_key(private_key)
    artifact_path = deploy_mod.DELEGATE_PROXY_CALLER_ARTIFACT
    abi = deploy_mod.load_contract_abi(artifact_path)
    bytecode = deploy_mod.load_contract_bytecode(artifact_path)

    print(f"Deploying DelegateProxyCaller from EVM {account.address} …")
    contract_address, _, tx_hash = deploy_mod.deploy_contract(
        w3, account, abi, bytecode
    )
    contract_address = Web3.to_checksum_address(contract_address)
    print(f"Deployed at {contract_address}, tx {tx_hash.hex()}")

    ss58_fmt = getattr(subtensor.substrate, "ss58_format", 42)
    contract_ss58 = h160_to_ss58(contract_address, ss58_prefix=ss58_fmt)
    print(f"Contract SS58 (delegate): {contract_ss58}")

    print(f"Adding proxy type={proxy_type!r} delay={proxy_delay} …")
    add_proxy_extrinsic(
        subtensor,
        wallet,
        contract_ss58,
        proxy_type=proxy_type,
        delay=proxy_delay,
        wait_for_inclusion=True,
        wait_for_finalization=False,
    )
    print("Done.")

    deployment_info = {
        "contract_address": contract_address,
        "contract_ss58": contract_ss58,
        "principal_ss58": delegate_ss58.strip(),
        "proxy_type": proxy_type,
        "proxy_delay": proxy_delay,
        "deployer_evm": account.address,
        "evm_tx": tx_hash.hex(),
        "chain_id": w3.eth.chain_id,
        "abi": abi,
    }
    out_path = os.path.join(PROJECT_ROOT, "deployment.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(deployment_info, f, indent=2)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
