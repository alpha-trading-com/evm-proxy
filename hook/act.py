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
from app.services.stake_service import do_stake, resolve_stake_amount

WHITELISTED_SUBNETS = [40, 58]
STAKE_EVENT_TYPES = {"START_CALL", "SUBMIT_ENCRYPTED"}


def add_stake(netuid: int, amount_tao: float | None = None, hotkey: str | None = None) -> dict:
    """Stake TAO on netuid via EVM proxy (add_stake). amount_tao=None stakes nearly all free balance."""
    hotkey = hotkey or settings.DEFAULT_DEST_HOTKEY
    amount_rao = resolve_stake_amount(amount_tao)
    return do_stake(hotkey, netuid, amount_rao)


if __name__ == "__main__":
    add_stake(28, 1)

