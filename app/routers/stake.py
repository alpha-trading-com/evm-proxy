"""Stake, stake-limit, remove-stake, remove-stake-limit, move-stake APIs."""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.auth import get_current_username
from app.schemas import (
    StakeBody,
    StakeLimitBody,
    StakeIfPriceBody,
    RemoveStakeBody,
    RemoveStakeLimitBody,
    RemoveStakeIfPriceBody,
    MoveStakeBody,
)
from app.services.stake_service import (
    do_stake,
    do_stake_limit,
    do_stake_if_price,
    do_stake_limit_if_price,
    do_remove_stake,
    do_remove_stake_limit,
    do_remove_stake_if_price,
    do_remove_stake_limit_if_price,
    do_move_stake,
    resolve_stake_amount,
    resolve_remove_stake_amount,
    resolve_remove_stake_limit_amounts,
    resolve_move_stake_amount,
)

router = APIRouter(prefix="/api", tags=["stake"])


@router.post("/stake")
async def api_stake(body: StakeBody, _: str = Depends(get_current_username)):
    try:
        amount_rao = resolve_stake_amount(body.amount_tao)
        return do_stake(body.hotkey, body.netuid, amount_rao)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@router.post("/stake-limit")
async def api_stake_limit(body: StakeLimitBody, _: str = Depends(get_current_username)):
    try:
        amount_rao = resolve_stake_amount(body.amount_tao)
        return do_stake_limit(
            body.hotkey,
            body.netuid,
            amount_rao,
            body.rate_tolerance,
            body.use_min_tolerance,
            body.allow_partial,
        )
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@router.post("/stake-if-price")
async def api_stake_if_price(body: StakeIfPriceBody, _: str = Depends(get_current_username)):
    try:
        amount_rao = resolve_stake_amount(body.amount_tao)
        if body.not_limited:
            return do_stake_if_price(
                body.hotkey,
                body.netuid,
                amount_rao,
                body.ref_price_tao_per_alpha,
                body.require_above,
            )
        return do_stake_limit_if_price(
            body.hotkey,
            body.netuid,
            amount_rao,
            body.rate_tolerance,
            body.use_min_tolerance,
            body.allow_partial,
            body.ref_price_tao_per_alpha,
            body.require_above,
        )
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@router.post("/remove-stake")
async def api_remove_stake(body: RemoveStakeBody, _: str = Depends(get_current_username)):
    try:
        amount_alpha_rao = resolve_remove_stake_amount(
            body.hotkey, body.netuid, body.amount
        )
        return do_remove_stake(body.hotkey, body.netuid, amount_alpha_rao)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@router.post("/remove-stake-limit")
async def api_remove_stake_limit(
    body: RemoveStakeLimitBody, _: str = Depends(get_current_username)
):
    try:
        amount_alpha_rao, amount_tao = resolve_remove_stake_limit_amounts(
            body.hotkey, body.netuid, body.amount
        )
        return do_remove_stake_limit(
            body.hotkey,
            body.netuid,
            amount_alpha_rao,
            body.rate_tolerance,
            body.use_min_tolerance,
            body.allow_partial,
            amount_tao,
        )
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@router.post("/remove-stake-if-price")
async def api_remove_stake_if_price(
    body: RemoveStakeIfPriceBody, _: str = Depends(get_current_username)
):
    try:
        if body.not_limited:
            amount_alpha_rao = resolve_remove_stake_amount(
                body.hotkey, body.netuid, body.amount
            )
            return do_remove_stake_if_price(
                body.hotkey,
                body.netuid,
                amount_alpha_rao,
                body.ref_price_tao_per_alpha,
                body.require_above,
            )
        amount_alpha_rao, amount_tao = resolve_remove_stake_limit_amounts(
            body.hotkey, body.netuid, body.amount
        )
        return do_remove_stake_limit_if_price(
            body.hotkey,
            body.netuid,
            amount_alpha_rao,
            body.rate_tolerance,
            body.use_min_tolerance,
            body.allow_partial,
            amount_tao,
            body.ref_price_tao_per_alpha,
            body.require_above,
        )
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@router.post("/move-stake")
async def api_move_stake(body: MoveStakeBody, _: str = Depends(get_current_username)):
    try:
        amount_rao = resolve_move_stake_amount(
            body.origin_hotkey, body.origin_netuid, body.amount_tao
        )
        return do_move_stake(
            body.origin_hotkey,
            body.destination_hotkey,
            body.origin_netuid,
            body.destination_netuid,
            amount_rao,
        )
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
