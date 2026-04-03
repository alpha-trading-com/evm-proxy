#!/usr/bin/env python3
"""
CLI for the deployed DelegateProxyCaller contract.

Supports:
- owner: show owner and whether current key is owner
- balance: show contract balance
- proxyCall: call DelegateProxyCaller.proxyCall(realAccountId32, proxyType, callBytes)
"""

import os
import sys
import argparse

_script_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_script_dir)
if _root not in sys.path:
    sys.path.insert(0, _root)

from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

from evm.contract import load_deployment_info
from evm.delegate_proxy import get_contract, proxy_call_with_runtime_call

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description='Interact with DelegateProxyCaller contract')
    parser.add_argument('action', choices=['owner', 'balance', 'proxyCall'],
                        help='Action to perform')
    parser.add_argument('--contract', type=str, help='Contract address (overrides deployment.json)')
    parser.add_argument('--real-account-id32', dest='real_account_id32', type=str,
                        help='Real AccountId32 as 0x-prefixed 32-byte hex string')
    parser.add_argument('--proxy-type', dest='proxy_type', type=int,
                        help='Proxy type index (e.g. 0 = Any)')
    parser.add_argument('--call-bytes', dest='call_bytes', type=str,
                        help='SCALE-encoded RuntimeCall bytes as 0x-prefixed hex string')

    args = parser.parse_args()
    
    # Load environment variables
    rpc_url = os.getenv('RPC_URL', 'https://test.finney.opentensor.ai/')
    private_key = os.getenv('PRIVATE_KEY')
    
    if not private_key:
        raise ValueError("PRIVATE_KEY environment variable is required")
    
    # Connect to blockchain
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise ConnectionError(f"Failed to connect to {rpc_url}")
    
    # Load account
    account = Account.from_key(private_key)
    
    if args.contract:
        contract_address = Web3.to_checksum_address(args.contract)
        abi = None
    else:
        deployment_info = load_deployment_info()
        contract_address = Web3.to_checksum_address(deployment_info["contract_address"])
        abi = deployment_info.get("abi") or None

    print(f"Contract address: {contract_address}")
    print(f"Account: {account.address}")

    contract = get_contract(w3, contract_address, abi=abi)

    # Execute action
    if args.action == 'owner':
        owner = contract.functions.owner().call()
        print(f"Contract owner: {owner}")
        print(f"Your account: {account.address}")
        if owner.lower() == account.address.lower():
            print("✅ You are the contract owner")
        else:
            print("❌ You are NOT the contract owner")
            print("   You need to use the owner's private key to withdraw")
    
    elif args.action == 'balance':
        balance_wei = w3.eth.get_balance(contract_address)  # Balance is in wei (10^18)
        balance_tao = Web3.from_wei(balance_wei, 'ether')
        print(f"Contract balance: {balance_tao} TAO ({balance_wei} wei)")
        print(f"Note: Balance is in wei (10^18).")

    elif args.action == "proxyCall":
        if not all([args.real_account_id32, args.proxy_type is not None, args.call_bytes]):
            parser.error("proxyCall requires --real-account-id32, --proxy-type, and --call-bytes")
        try:
            proxy_call_with_runtime_call(
                w3,
                account,
                contract_address,
                proxy_type=int(args.proxy_type),
                runtime_call=args.call_bytes,
                real_account_id32=args.real_account_id32,
                gas=500_000,
                contract=contract,
            )
        except ValueError as e:
            parser.error(str(e))

if __name__ == '__main__':
    main()

