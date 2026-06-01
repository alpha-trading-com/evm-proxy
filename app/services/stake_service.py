"""Stake/unstake amount resolution and EVM stake calls. Depends on subtensor for chain state."""
import bittensor as bt
import os
import sys
from web3 import Web3

from app.globals import get_coldkey_ss58, get_subtensor
from app.services.evm_service import get_w3_account_contract, receipt_to_dict, run_quiet
from app.services.evm import (
    move_stake,
    remove_stake,
    remove_stake_if_price,
    remove_stake_limit,
    remove_stake_limit_if_price,
    stake,
    stake_if_price,
    stake_limit,
    stake_limit_if_price,
)
from utils.tolerance import calculate_stake_limit_price, calculate_unstake_limit_price
from app.core.config import settings


def get_stake_custom(
    subtensor: bt.Subtensor, coldkey_ss58: str, hotkey_ss58: str, netuid: int, block: int | None = None
) -> bt.Balance:
    """
    Get the stake for a given hotkey/coldkey pair.

    NOTE: This function was needed because of a breaking change in bittensor SDK that was released 2026-04-24
    that broke the subtensor.get_stake function. When we migrate to bittensor to >= 10.2.0, this function can be
    removed and we can revert to using the subtensor.get_stake function.
    """
    result = subtensor.query_runtime_api(
        runtime_api="StakeInfoRuntimeApi",
        method="get_stake_info_for_hotkey_coldkey_netuid",
        params=[hotkey_ss58, coldkey_ss58, netuid],
        block=block,
    )
    stake = bt.Balance.from_rao(result["stake"]).set_unit(netuid)
    return stake


def resolve_stake_amount(amount_tao: float | None) -> int:
    """Convert stake amount (None = all free balance, 0<x<1 = fraction) to rao."""
    subtensor = get_subtensor()
    coldkey_ss58 = settings.REAL_ACCOUNT_SS58
    if amount_tao is None:
        free_balance = subtensor.get_balance(coldkey_ss58)
        return max(0, int(free_balance.rao) - 10**9)
    if 0 < amount_tao < 1:
        free_balance = subtensor.get_balance(coldkey_ss58)
        return int(amount_tao * free_balance.rao)
    return int(amount_tao * 10**9)


def resolve_remove_stake_amount(
    hotkey: str, netuid: int, amount: float | None
) -> int:
    """Convert remove_stake amount (None = all, 0<x<1 = fraction) to alpha rao."""
    coldkey_ss58 = settings.REAL_ACCOUNT_SS58
    subtensor = get_subtensor()
    print(amount, file=sys.stdout)
    if amount is None:
        stake_balance = get_stake_custom(subtensor=subtensor, coldkey_ss58=coldkey_ss58, hotkey_ss58=hotkey, netuid=netuid)
        return max(0, int(stake_balance.rao) - 1)
    if 0 < amount < 1:
        stake_balance = get_stake_custom(subtensor=subtensor, coldkey_ss58=coldkey_ss58, hotkey_ss58=hotkey, netuid=netuid)
        print(stake_balance, file=sys.stdout)
        return int(amount * stake_balance.rao)
    return int(amount * 10**9)


def resolve_remove_stake_limit_amounts(
    hotkey: str, netuid: int, amount: float | None
) -> tuple[int, float]:
    """Return (amount_alpha_rao, amount_tao) for remove_stake_limit."""
    coldkey_ss58 = settings.REAL_ACCOUNT_SS58
    subtensor = get_subtensor()
    if amount is None:
        stake_balance = get_stake_custom(subtensor=subtensor, coldkey_ss58=coldkey_ss58, hotkey_ss58=hotkey, netuid=netuid)
        return stake_balance.rao - 1, stake_balance.tao
    if 0 < amount < 1:
        stake_balance = get_stake_custom(subtensor=subtensor, coldkey_ss58=coldkey_ss58, hotkey_ss58=hotkey, netuid=netuid)
        return int(amount * stake_balance.rao), amount * stake_balance.tao
    return int(amount * 10**9), amount / 10**9


def resolve_move_stake_amount(
    origin_hotkey: str, origin_netuid: int, amount_tao: float | None
) -> int:
    """Convert move_stake amount (None = all, 0<x<1 = fraction) to rao."""
    coldkey_ss58 = settings.REAL_ACCOUNT_SS58
    subtensor = get_subtensor()
    if amount_tao is None:
        stake_balance = get_stake_custom(
            subtensor=subtensor,
            coldkey_ss58=coldkey_ss58, hotkey_ss58=origin_hotkey, netuid=origin_netuid
        )
        return max(0, int(stake_balance.rao) - 1)
    if 0 < amount_tao < 1:
        stake_balance = get_stake_custom(
            subtensor=subtensor,
            coldkey_ss58=coldkey_ss58, hotkey_ss58=origin_hotkey, netuid=origin_netuid
        )
        return int(amount_tao * stake_balance.rao)
    return int(amount_tao * 10**9)


def do_stake(hotkey: str, netuid: int, amount_rao: int) -> dict:
    w3, account, contract_address, contract = get_w3_account_contract()
    receipt = run_quiet(stake, w3, account, contract_address, hotkey, netuid, amount_rao, contract=contract)
    return {"ok": True, "receipt": receipt_to_dict(receipt)}


def _ref_price_rao(ref_price_tao_per_alpha: float) -> int:
    return int(ref_price_tao_per_alpha * 10**9)


def do_stake_if_price(
    hotkey: str,
    netuid: int,
    amount_rao: int,
    ref_price_tao_per_alpha: float,
    require_above: bool,
) -> dict:
    ref_rao = _ref_price_rao(ref_price_tao_per_alpha)
    w3, account, contract_address, contract = get_w3_account_contract()
    receipt = run_quiet(
        stake_if_price,
        w3,
        account,
        contract_address,
        hotkey,
        netuid,
        amount_rao,
        ref_rao,
        require_above,
        contract=contract,
    )
    return {
        "ok": True,
        "receipt": receipt_to_dict(receipt),
        "ref_price_rao_per_alpha_used": ref_rao,
    }


def do_stake_limit_if_price(
    hotkey: str,
    netuid: int,
    amount_rao: int,
    rate_tolerance: float,
    use_min_tolerance: bool,
    allow_partial: bool,
    ref_price_tao_per_alpha: float,
    require_above: bool,
) -> dict:
    subtensor = get_subtensor()
    limit_price = int(
        calculate_stake_limit_price(
            tao_amount=amount_rao / 10**9,
            netuid=netuid,
            min_tolerance_staking=use_min_tolerance,
            default_rate_tolerance=rate_tolerance,
            subtensor=subtensor,
        )
    )
    ref_rao = _ref_price_rao(ref_price_tao_per_alpha)
    w3, account, contract_address, contract = get_w3_account_contract()
    receipt = run_quiet(
        stake_limit_if_price,
        w3,
        account,
        contract_address,
        hotkey,
        netuid,
        limit_price,
        amount_rao,
        allow_partial,
        ref_rao,
        require_above,
        contract=contract,
    )
    return {
        "ok": True,
        "receipt": receipt_to_dict(receipt),
        "limit_price_used": limit_price,
        "ref_price_rao_per_alpha_used": ref_rao,
    }


def do_stake_limit(
    hotkey: str, netuid: int, amount_rao: int,
    rate_tolerance: float, use_min_tolerance: bool, allow_partial: bool,
) -> dict:
    subtensor = get_subtensor()
    limit_price = int(calculate_stake_limit_price(
        tao_amount=amount_rao / 10**9,
        netuid=netuid,
        min_tolerance_staking=use_min_tolerance,
        default_rate_tolerance=rate_tolerance,
        subtensor=subtensor,
    ))
    w3, account, contract_address, contract = get_w3_account_contract()
    receipt = run_quiet(
        stake_limit, w3, account, contract_address,
        hotkey, netuid, limit_price, amount_rao, allow_partial,
        contract=contract,
    )
    return {"ok": True, "receipt": receipt_to_dict(receipt), "limit_price_used": limit_price}


def do_remove_stake(hotkey: str, netuid: int, amount_alpha_rao: int) -> dict:
    w3, account, contract_address, contract = get_w3_account_contract()
    receipt = run_quiet(
        remove_stake, w3, account, contract_address, hotkey, netuid, amount_alpha_rao,
        contract=contract,
    )
    return {"ok": True, "receipt": receipt_to_dict(receipt)}


def do_remove_stake_if_price(
    hotkey: str,
    netuid: int,
    amount_alpha_rao: int,
    ref_price_tao_per_alpha: float,
    require_above: bool,
) -> dict:
    ref_rao = _ref_price_rao(ref_price_tao_per_alpha)
    w3, account, contract_address, contract = get_w3_account_contract()
    receipt = run_quiet(
        remove_stake_if_price,
        w3,
        account,
        contract_address,
        hotkey,
        netuid,
        amount_alpha_rao,
        ref_rao,
        require_above,
        contract=contract,
    )
    return {
        "ok": True,
        "receipt": receipt_to_dict(receipt),
        "ref_price_rao_per_alpha_used": ref_rao,
    }


def do_remove_stake_limit_if_price(
    hotkey: str,
    netuid: int,
    amount_alpha_rao: int,
    rate_tolerance: float,
    use_min_tolerance: bool,
    allow_partial: bool,
    amount_tao: float,
    ref_price_tao_per_alpha: float,
    require_above: bool,
) -> dict:
    subtensor = get_subtensor()
    limit_price = int(
        calculate_unstake_limit_price(
            tao_amount=amount_tao,
            netuid=netuid,
            min_tolerance_unstaking=use_min_tolerance,
            default_rate_tolerance=rate_tolerance,
            subtensor=subtensor,
        )
    )
    ref_rao = _ref_price_rao(ref_price_tao_per_alpha)
    w3, account, contract_address, contract = get_w3_account_contract()
    receipt = run_quiet(
        remove_stake_limit_if_price,
        w3,
        account,
        contract_address,
        hotkey,
        netuid,
        limit_price,
        amount_alpha_rao,
        allow_partial,
        ref_rao,
        require_above,
        contract=contract,
    )
    return {
        "ok": True,
        "receipt": receipt_to_dict(receipt),
        "limit_price_used": limit_price,
        "ref_price_rao_per_alpha_used": ref_rao,
    }


def do_remove_stake_limit(
    hotkey: str, netuid: int, amount_alpha_rao: int,
    rate_tolerance: float, use_min_tolerance: bool, allow_partial: bool,
    amount_tao: float,
) -> dict:
    subtensor = get_subtensor()
    limit_price = int(calculate_unstake_limit_price(
        tao_amount=amount_tao,
        netuid=netuid,
        min_tolerance_unstaking=use_min_tolerance,
        default_rate_tolerance=rate_tolerance,
        subtensor=subtensor,
    ))
    w3, account, contract_address, contract = get_w3_account_contract()
    receipt = run_quiet(
        remove_stake_limit, w3, account, contract_address,
        hotkey, netuid, limit_price, amount_alpha_rao, allow_partial,
        contract=contract,
    )
    return {"ok": True, "receipt": receipt_to_dict(receipt), "limit_price_used": limit_price}

def do_move_stake(
    origin_hotkey: str, destination_hotkey: str,
    origin_netuid: int, destination_netuid: int, amount_rao: int,
) -> dict:
    w3, account, contract_address, contract = get_w3_account_contract()
    receipt = run_quiet(
        move_stake, w3, account, contract_address,
        origin_hotkey, destination_hotkey, origin_netuid, destination_netuid, amount_rao,
        contract=contract,
    )
    return {"ok": True, "receipt": receipt_to_dict(receipt)}
