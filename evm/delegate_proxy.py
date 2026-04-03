"""
DelegateProxyCaller contract interaction helpers.

This module is the canonical home for DelegateProxyCaller helpers. It mirrors
the old evm.stake_wrap API but targets the DelegateProxyCaller contract:

- owner() view returns (address)
- proxyCall(bytes32 realAccountId32, uint8 proxyType, bytes call)
"""

from typing import Any, Dict, List, Optional, Union

from eth_account import Account
from web3 import Web3
from web3.types import TxReceipt

from evm.address import ss58_to_bytes32
from evm.contract import get_contract as _evm_get_contract, get_stake_wrap_abi
from utils.substrate_runtime_call import runtime_call_bytes

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


def _coerce_real_account_id32(
    *,
    real_account_id32: Optional[Union[str, bytes]] = None,
    delegator_ss58: Optional[str] = None,
) -> bytes:
    if delegator_ss58 is not None and delegator_ss58.strip():
        if real_account_id32 is not None:
            raise ValueError("Use only one of delegator_ss58 or real_account_id32")
        return ss58_to_bytes32(delegator_ss58.strip())
    if real_account_id32 is None:
        raise ValueError("Provide delegator_ss58 or real_account_id32")
    if isinstance(real_account_id32, bytes):
        if len(real_account_id32) != 32:
            raise ValueError("real_account_id32 bytes must be length 32")
        return real_account_id32
    s = str(real_account_id32).strip()
    if s.startswith(("0x", "0X")):
        s = s[2:]
    b = bytes.fromhex(s)
    if len(b) != 32:
        raise ValueError("real_account_id32 hex must decode to 32 bytes")
    return b


def proxy_call_with_runtime_call(
    w3: Web3,
    account: Account,
    contract_address: str,
    *,
    proxy_type: int,
    runtime_call: Any,
    delegator_ss58: Optional[str] = None,
    real_account_id32: Optional[Union[str, bytes]] = None,
    gas: int = 2_000_000,
    contract=None,
    verbose: bool = True,
) -> TxReceipt:
    """
    Submit ``DelegateProxyCaller.proxyCall`` using SCALE-encoded inner call / extrinsic payload.

    ``runtime_call`` may be:

    - ``bytes`` / ``bytearray``
    - hex ``str`` (``RuntimeCall`` bytes)
    - result of ``subtensor.substrate.compose_call(...)``

    The **owner** ``account`` signs the EVM tx; ``delegator_ss58`` / ``real_account_id32`` is the
    real Substrate account that added this contract as a proxy.
    """
    real_bytes = _coerce_real_account_id32(
        real_account_id32=real_account_id32,
        delegator_ss58=delegator_ss58,
    )
    call_bytes = runtime_call_bytes(runtime_call)

    if contract is None:
        contract = get_contract(w3, contract_address)

    tx = contract.functions.proxyCall(
        real_bytes,
        int(proxy_type),
        call_bytes,
    ).build_transaction(
        {
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": int(gas),
            "gasPrice": w3.eth.gas_price,
        }
    )
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    if verbose:
        print(f"proxyCall transaction hash: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if verbose:
        print(
            f"Transaction confirmed in block: {receipt.blockNumber}, status={receipt.status}"
        )
    return receipt


def proxy_call(
    w3,
    account: Account,
    contract_address: str,
    real_account_id32_hex: str,
    proxy_type: int,
    call_bytes_hex: str,
    contract=None,
    gas: int = 500_000,
    verbose: bool = True,
):
    """
    Call DelegateProxyCaller.proxyCall(realAccountId32, proxyType, callBytes).

    - real_account_id32_hex: 0x-prefixed 32-byte hex AccountId32 of the real account.
    - proxy_type: proxy type index (e.g. 0 = Any).
    - call_bytes_hex: 0x-prefixed SCALE-encoded RuntimeCall bytes.
    """
    return proxy_call_with_runtime_call(
        w3,
        account,
        contract_address,
        proxy_type=proxy_type,
        runtime_call=call_bytes_hex,
        real_account_id32=real_account_id32_hex,
        gas=gas,
        contract=contract,
        verbose=verbose,
    )
