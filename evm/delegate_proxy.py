"""
DelegateProxyCaller contract interaction helpers.

This module is the canonical home for DelegateProxyCaller helpers. It mirrors
the old evm.stake_wrap API but targets the DelegateProxyCaller contract:

- owner() view returns (address)
- proxyCall(bytes32 realAccountId32, uint8 proxyType, bytes call)
"""

from typing import Any, Dict, List, Optional

from web3 import Web3
from eth_account import Account

from evm.contract import get_contract as _evm_get_contract, get_stake_wrap_abi

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


def proxy_call(
    w3,
    account: Account,
    contract_address: str,
    real_account_id32_hex: str,
    proxy_type: int,
    call_bytes_hex: str,
    contract=None,
):
    """
    Call DelegateProxyCaller.proxyCall(realAccountId32, proxyType, callBytes).

    - real_account_id32_hex: 0x-prefixed 32-byte hex AccountId32 of the real account.
    - proxy_type: proxy type index (e.g. 0 = Any).
    - call_bytes_hex: 0x-prefixed SCALE-encoded RuntimeCall bytes.
    """
    if contract is None:
        contract = get_contract(w3, contract_address)

    real_hex = real_account_id32_hex
    if real_hex.startswith("0x") or real_hex.startswith("0X"):
        real_hex = real_hex[2:]
    real_bytes = bytes.fromhex(real_hex)
    if len(real_bytes) != 32:
        raise ValueError("real_account_id32_hex must be 32 bytes (64 hex chars after 0x)")

    call_hex = call_bytes_hex
    if call_hex.startswith("0x") or call_hex.startswith("0X"):
        call_hex = call_hex[2:]
    call_bytes = bytes.fromhex(call_hex)

    tx = contract.functions.proxyCall(
        real_bytes,
        int(proxy_type),
        call_bytes,
    ).build_transaction(
        {
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 500_000,
            "gasPrice": w3.eth.gas_price,
        }
    )
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"proxyCall transaction hash: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction confirmed in block: {receipt.blockNumber}, status={receipt.status}")
    return receipt

