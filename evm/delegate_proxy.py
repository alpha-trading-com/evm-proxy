"""
DelegateProxyCaller contract interaction helpers.

This module is the canonical home for DelegateProxyCaller helpers. It mirrors
the old evm.stake_wrap API but targets the DelegateProxyCaller contract:

- owner() view returns (address)
- proxyCall(bytes32 realAccountId32, uint8 proxyType, bytes call)
"""

import sys
from typing import Any, Dict, List, Optional, TypeAlias

from eth_account import Account
from web3 import Web3
from web3.types import TxReceipt

from evm.address import ss58_to_bytes32
from evm.contract import get_contract as _evm_get_contract, get_stake_wrap_abi
from utils.substrate_runtime_call import runtime_call_bytes

# Real account on whose behalf the proxy runs (Substrate SS58, e.g. ``5GrwvaEF...``).
SS58: TypeAlias = str

# Minimal ABI for DelegateProxyCaller interaction (fallback when artifact missing)
CONTRACT_ABI: List[Dict[str, Any]] = [
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "realAccountId32", "type": "bytes32"},
            {"internalType": "uint8", "name": "proxyType", "type": "uint8"},
            {"internalType": "bytes", "name": "call", "type": "bytes"},
        ],
        "name": "proxyCall",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


def get_contract(w3, contract_address: str, abi: Optional[List[Dict[str, Any]]] = None):
    """
    DelegateProxyCaller contract instance; uses artifact ABI when available,
    else CONTRACT_ABI.
    """
    if abi is None:
        abi = get_stake_wrap_abi() or CONTRACT_ABI
    return _evm_get_contract(w3, contract_address, abi=abi)


def proxy_call_with_runtime_call(
    w3: Web3,
    account: Account,
    contract_address: str,
    *,
    proxy_type: int,
    runtime_call: Any,
    real_ss58: SS58,
    contract=None,
) -> TxReceipt:
    """
    Submit ``DelegateProxyCaller.proxyCall`` using SCALE-encoded inner call / extrinsic payload.

    ``runtime_call`` may be:

    - ``bytes`` / ``bytearray``
    - hex ``str`` (``RuntimeCall`` bytes)
    - result of ``substrate.compose_call(...)``

    ``real_ss58``: the real account's **SS58** address (decoded to ``AccountId32`` for the precompile).
    The **owner** ``account`` signs the EVM tx.
    """
    real_bytes = ss58_to_bytes32(real_ss58.strip())
    print(real_bytes, file=sys.stderr)
    call_bytes = runtime_call_bytes(runtime_call)
    print(call_bytes, file=sys.stderr)

    if contract is None:
        contract = get_contract(w3, contract_address)

    print("test2", file=sys.stderr)

    tx = contract.functions.proxyCall(
        real_bytes,
        int(proxy_type),
        call_bytes,
    ).build_transaction(
        {
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": int(2000000),
            "gasPrice": w3.eth.gas_price,
        }
    )
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print("test3", file=sys.stderr)
    return receipt
