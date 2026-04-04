from web3 import Web3
from eth_account import Account
from app.services.extrinsics import (
    add_stake_extrinsic,
    add_stake_limit_extrinsic,
    remove_stake_extrinsic,
    remove_stake_limit_extrinsic,
    move_stake_extrinsic,
)
from app.core.config import settings
from evm import proxy_call_with_runtime_call
from utils.substrate_runtime_call import runtime_call_bytes


def stake(
    w3: Web3, 
    account: Account, 
    contract_address: str,
    hotkey: str, 
    netuid: int, 
    amount_rao: int,
    contract=None,
) -> dict:
    call = add_stake_extrinsic(
        w3,
        account,
        contract_address,
        hotkey,
        netuid,
        amount_rao,
    )
    inner = runtime_call_bytes(call)
    receipt = proxy_call_with_runtime_call(
        w3,
        account,
        contract_address,
        proxy_type=0,
        runtime_call=inner,
        real_ss58=settings.DELEGATOR_SS58,
        contract=contract,
    )
    return receipt


def stake_limit(
    w3: Web3, 
    account: Account, 
    contract_address: str,
    hotkey: str, 
    netuid: int, 
    limit_price: int, 
    amount_rao: int, 
    allow_partial: bool,
    contract=None,
) -> dict:
    call = add_stake_limit_extrinsic(
        w3,
        account,
        contract_address,
        hotkey,
        netuid,
        limit_price,
        amount_rao,
        allow_partial,
    )
    inner = runtime_call_bytes(call)
    receipt = proxy_call_with_runtime_call(
        w3,
        account,
        contract_address,
        proxy_type=0,
        runtime_call=inner,
        real_ss58=settings.DELEGATOR_SS58,
        contract=contract,
    )

    return receipt


def remove_stake(
    w3: Web3, 
    account: Account, 
    contract_address: str,
    hotkey: str, 
    netuid: int, 
    amount_rao: int,
    contract=None,
) -> dict:
    call = remove_stake_extrinsic(
        w3,
        account,
        contract_address,
        hotkey,
        netuid,
        amount_rao,
    )
    inner = runtime_call_bytes(call)
    receipt = proxy_call_with_runtime_call(
        w3,
        account,
        contract_address,
        proxy_type=0,
        runtime_call=inner,
        real_ss58=settings.DELEGATOR_SS58,
        contract=contract,
    )

    return receipt


def remove_stake_limit(
    w3: Web3, 
    account: Account, 
    contract_address: str,
    hotkey: str, 
    netuid: int, 
    amount_rao: int,
    contract=None,
) -> dict:
    call = remove_stake_limit_extrinsic(
        w3,
        account,
        contract_address,
        hotkey,
        netuid,
        amount_rao,
    )
    inner = runtime_call_bytes(call)
    receipt = proxy_call_with_runtime_call(
        w3,
        account,
        contract_address,
        proxy_type=0,
        runtime_call=inner,
        real_ss58=settings.DELEGATOR_SS58,
        contract=contract,
    )

    return receipt


def move_stake(
    w3: Web3, 
    account: Account, 
    contract_address: str,
    origin_hotkey: str, 
    destination_hotkey: str, 
    origin_netuid: int, 
    destination_netuid: int, 
    amount_rao: int,
    contract=None,
) -> dict:
    call = move_stake_extrinsic(
        w3,
        account,
        contract_address,
        origin_hotkey,
        destination_hotkey,
        origin_netuid,
        destination_netuid,
        amount_rao,
    )
    inner = runtime_call_bytes(call)
    receipt = proxy_call_with_runtime_call(
        w3,
        account,
        contract_address,
        proxy_type=0,
        runtime_call=inner,
        real_ss58=settings.DELEGATOR_SS58,
        contract=contract,
    )
    return receipt

