import bittensor as bt
import sys
from app.core.config import settings

def proxy_call_extrinsic(
    subtensor: bt.Subtensor,
    delegator: str,
    call,
    proxy_type: str = 'Staking',
) -> tuple[bool, str]:
    proxy_call = subtensor.substrate.compose_call(
        call_module='Proxy',
        call_function='proxy',
        call_params={
            'real': delegator,
            'force_proxy_type': proxy_type,
            'call': call,
        }
    )
    return proxy_call

def add_stake_extrinsic(
    subtensor: bt.Subtensor,
    hotkey: str,
    netuid: int,
    amount: int,
) -> dict:
    print("test1", file=sys.stderr)
    print(hotkey, file=sys.stderr)
    print(netuid, file=sys.stderr)
    print(amount, file=sys.stderr)
    call = subtensor.substrate.compose_call(
        call_module='SubtensorModule',
        call_function='add_stake',
        call_params={
            "hotkey": hotkey,
            "netuid": netuid,
            "amount_staked": amount,
        }
    )
    proxied_call = proxy_call_extrinsic(
        subtensor,
        settings.REAL_ACCOUNT_SS58,
        call,
        proxy_type="Staking",
    )
    print("test2", file=sys.stderr)
    return proxied_call

def add_stake_limit_extrinsic(
    subtensor: bt.Subtensor,
    hotkey: str,
    netuid: int,
    amount: int,
    price_with_tolerance: int,
    allow_partial: bool,
) -> dict:
    call = subtensor.substrate.compose_call(
            call_module='SubtensorModule',
            call_function='add_stake_limit',
            call_params={
                "hotkey": hotkey,
                "netuid": netuid,
                "amount_staked": amount,
                "limit_price": price_with_tolerance,
                "allow_partial": allow_partial,
            }
        )

    proxied_call = proxy_call_extrinsic(
        subtensor,
        settings.REAL_ACCOUNT_SS58,
        call,
        proxy_type="Staking",
    )
    return proxied_call


def remove_stake_extrinsic(
    subtensor: bt.Subtensor,
    hotkey: str,
    netuid: int,
    amount: int,
) -> dict:
    call = subtensor.substrate.compose_call(
        call_module='SubtensorModule',
        call_function='remove_stake',
        call_params={
            "hotkey": hotkey,
            "netuid": netuid,
            "amount_unstaked": amount,
        }
    )
    proxied_call = proxy_call_extrinsic(
        subtensor,
        settings.REAL_ACCOUNT_SS58,
        call,
        proxy_type="Staking",
    )
    return proxied_call


def remove_stake_limit_extrinsic(
    subtensor: bt.Subtensor,
    hotkey: str,
    netuid: int,
    amount: int,
    price_with_tolerance: int,
    allow_partial: bool,
) -> dict:
    call = subtensor.substrate.compose_call(
        call_module='SubtensorModule',
        call_function='remove_stake_limit',
        call_params={
            "hotkey": hotkey,
            "netuid": netuid,
            "amount_unstaked": amount,
            "limit_price": price_with_tolerance,
            "allow_partial": allow_partial,         
        }
    )
    proxied_call = proxy_call_extrinsic(
        subtensor,
        settings.REAL_ACCOUNT_SS58,
        call,
        proxy_type="Staking",
    )
    return proxied_call


def move_stake_extrinsic(
    subtensor: bt.Subtensor,
    origin_hotkey: str,
    destination_hotkey: str,
    origin_netuid: int,
    destination_netuid: int,
    amount: int,
) -> dict:
    call = subtensor.substrate.compose_call(
        call_module='SubtensorModule',
        call_function='move_stake',
        call_params={
            "origin_hotkey": origin_hotkey,
            "destination_hotkey": destination_hotkey,
            "origin_netuid": origin_netuid,
            "destination_netuid": destination_netuid,
            "alpha_amount": amount,
        }
    )
    proxied_call = proxy_call_extrinsic(
        subtensor,
        settings.REAL_ACCOUNT_SS58,
        call,
        proxy_type="Staking",
    )
    return proxied_call
