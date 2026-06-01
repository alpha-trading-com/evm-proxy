"""Submit add_stake when mempool events match whitelisted subnets."""
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv

load_dotenv(_REPO_ROOT / ".env")

from app.core.config import settings
from app.services.stake_service import do_stake, do_stake_if_price, resolve_stake_amount

WHITELISTED_SUBNETS = [40, 58]
STAKE_EVENT_TYPES = {"START_CALL", "SUBMIT_ENCRYPTED"}

# netuid -> (ref_price_tao_per_alpha, require_above)
SUBNET_STAKE_IF_PRICE: dict[int, tuple[float, bool]] = {
    40: (0.01, True),
    58: (0.01, True),
}


def add_stake(netuid: int, amount_tao: float | None = None, hotkey: str | None = None) -> dict:
    """Stake TAO on netuid via EVM proxy (add_stake). amount_tao=None stakes nearly all free balance."""
    hotkey = hotkey or settings.DEFAULT_DEST_HOTKEY
    amount_rao = resolve_stake_amount(amount_tao)
    if amount_rao <= 0:
        return {"ok": False, "reason": "no_balance", "netuid": netuid, "amount_rao": amount_rao}
    print(f"add_stake netuid={netuid} hotkey={hotkey} amount_rao={amount_rao}")
    return do_stake(hotkey, netuid, amount_rao)


def add_stake_if_price(
    netuid: int,
    ref_price_tao_per_alpha: float,
    require_above: bool = True,
    amount_tao: float | None = None,
    hotkey: str | None = None,
) -> dict:
    """
    Stake via add_stake only if subnet alpha price passes the reference check (EVM precompile gate).

    ref_price_tao_per_alpha: reference in TAO per alpha (same units as Stake Info "Price").
    require_above: True to stake only when price > ref; False when price < ref.
    """
    hotkey = hotkey or settings.DEFAULT_DEST_HOTKEY
    amount_rao = resolve_stake_amount(amount_tao)
    if amount_rao <= 0:
        return {"ok": False, "reason": "no_balance", "netuid": netuid, "amount_rao": amount_rao}
    print(
        f"add_stake_if_price netuid={netuid} hotkey={hotkey} amount_rao={amount_rao} "
        f"ref_price_tao_per_alpha={ref_price_tao_per_alpha} require_above={require_above}"
    )
    return do_stake_if_price(hotkey, netuid, amount_rao, ref_price_tao_per_alpha, require_above)


def process_events(events: list[dict]) -> list[dict]:
    """Run add_stake (or add_stake_if_price when configured) for whitelisted subnet events."""
    results = []
    for event in events:
        event_type = event.get("event_type")
        netuid = event.get("subnet")
        if event_type not in STAKE_EVENT_TYPES:
            continue
        if netuid not in WHITELISTED_SUBNETS:
            continue
        try:
            price_cfg = SUBNET_STAKE_IF_PRICE.get(netuid)
            if price_cfg is not None:
                ref_price, require_above = price_cfg
                result = add_stake_if_price(netuid, ref_price, require_above)
            else:
                result = add_stake(netuid)
            results.append({"event": event, "stake": result})
        except Exception as exc:
            print(f"stake failed for subnet {netuid}: {exc}")
            results.append({"event": event, "stake": {"ok": False, "error": str(exc)}})
    return results


if __name__ == "__main__":
    add_stake_if_price(28, ref_price_tao_per_alpha=0.01, require_above=True, amount_tao=1)
