#!/usr/bin/env python3
"""
Deploy the DelegateProxyCaller contract to the blockchain.
Writes deployment.json with address, ABI, and metadata.

Uses ``LegacyWebSocketProvider`` (see ``evm.web3_provider``); set ``RPC_URL`` or ``RPC_WS_URL``.
"""

import os
import sys
import json
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

# Project root for evm imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from evm.web3_provider import web3_legacy_ws

DELEGATE_PROXY_CALLER_ARTIFACT = os.path.join(
    PROJECT_ROOT, "artifacts", "contracts", "DelegateProxyCaller.sol", "DelegateProxyCaller.json"
)

load_dotenv()


def load_contract_abi(artifact_path):
    """Load contract ABI from Hardhat artifacts."""
    with open(artifact_path, 'r') as f:
        artifact = json.load(f)
    return artifact['abi']


def load_contract_bytecode(artifact_path):
    """Load contract bytecode from Hardhat artifacts."""
    with open(artifact_path, 'r') as f:
        artifact = json.load(f)
    return artifact['bytecode']


def deploy_contract(w3, account, contract_abi, contract_bytecode):
    """Deploy the contract and return the contract address, abi and tx hash."""
    # Create contract instance
    contract = w3.eth.contract(abi=contract_abi, bytecode=contract_bytecode)
    
    # Build transaction - no constructor parameters needed
    construct_txn = contract.constructor().build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 2000000,  # Adjust based on your needs
        'gasPrice': w3.eth.gas_price,
    })
    
    # Sign transaction
    signed_txn = account.sign_transaction(construct_txn)
    
    # Send transaction
    print(f"Deploying contract from {account.address}...")
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"Transaction hash: {tx_hash.hex()}")
    
    # Wait for receipt
    print("Waiting for transaction receipt...")
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Contract deployed at address: {tx_receipt.contractAddress}")
    
    return tx_receipt.contractAddress, contract_abi, tx_hash


def main():
    # Load environment variables
    rpc_url = os.getenv('RPC_URL', 'https://test.finney.opentensor.ai/')
    private_key = os.getenv('PRIVATE_KEY')
    
    if not private_key:
        raise ValueError("PRIVATE_KEY environment variable is required")
    
    w3 = web3_legacy_ws(rpc_url)
    if not w3.is_connected():
        raise ConnectionError(f"Failed to connect (WebSocket) for {rpc_url!r}")

    print(f"Connected via LegacyWebSocketProvider ({rpc_url!r})")
    print(f"Chain ID: {w3.eth.chain_id}")
    
    # Load account
    account = Account.from_key(private_key)
    print(f"Deploying from account: {account.address}")
    balance = w3.eth.get_balance(account.address)
    print(f"Account balance: {Web3.from_wei(balance, 'ether')} TAO")
    
    # Load contract artifacts (from repo: compile on build server, or `npm run compile` locally)
    artifact_path = DELEGATE_PROXY_CALLER_ARTIFACT
    if not os.path.exists(artifact_path):
        raise FileNotFoundError(
            f"Contract artifact not found at {artifact_path}. "
            "Run `npx hardhat compile` (or equivalent) so that "
            "artifacts/contracts/DelegateProxyCaller.sol/DelegateProxyCaller.json exists, "
            "then re-run this script."
        )
    
    contract_abi = load_contract_abi(artifact_path)
    contract_bytecode = load_contract_bytecode(artifact_path)
    
    # Deploy contract
    contract_address, abi, tx_hash = deploy_contract(
        w3, account, contract_abi, contract_bytecode
    )
    
    # Save deployment info
    deployment_info = {
        'contract_address': contract_address,
        'deployer': account.address,
        'chain_id': w3.eth.chain_id,
        'transaction_hash': tx_hash.hex(),
        'abi': abi
    }
    
    with open('deployment.json', 'w') as f:
        json.dump(deployment_info, f, indent=2)

    print(f"\nDeployment info saved to deployment.json")
    print(f"Contract Address: {contract_address}")


if __name__ == '__main__':
    main()

