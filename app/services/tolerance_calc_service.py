"""Min tolerance helpers for stake/unstake limit UI (uses shared Subtensor + utils.tolerance)."""

from __future__ import annotations

from app.globals import get_subtensor
from utils.tolerance import calculate_stake_limit_price, calculate_unstake_limit_price


def calc_min_tolerance_stake(tao_amount: float, netuid: int) -> tuple[int, float]:
    sub = get_subtensor()
    lp = int(
        calculate_stake_limit_price(
            tao_amount=tao_amount,
            netuid=netuid,
            min_tolerance_staking=True,
            default_rate_tolerance=0.5,
            subtensor=sub,
        )
    )
    if netuid == 0:
        return lp, 0.0
    subnet = sub.subnet(netuid=netuid)
    ref = float(subnet.price.rao)
    if ref <= 0:
        return lp, 0.0
    rate_tolerance = lp / ref - 1.0
    return lp, rate_tolerance


def calc_min_tolerance_unstake(tao_amount: float, netuid: int) -> tuple[int, float]:
    sub = get_subtensor()
    lp = int(
        calculate_unstake_limit_price(
            tao_amount=tao_amount,
            netuid=netuid,
            min_tolerance_unstaking=True,
            default_rate_tolerance=0.5,
            subtensor=sub,
        )
    )
    if netuid == 0:
        return lp, 0.0
    subnet = sub.subnet(netuid=netuid)
    ref = float(subnet.price.rao)
    if ref <= 0:
        return lp, 0.0
    rate_tolerance = 1.0 - lp / ref
    return lp, rate_tolerance
