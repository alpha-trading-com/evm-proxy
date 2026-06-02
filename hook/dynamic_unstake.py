import bittensor as bt
import time

"""Move stake to root (netuid 0) when subnet alpha price is above a threshold."""
import sys
from pathlib import Path
import bittensor as bt
import time
_REPO_ROOT = Path(__file__).resolve().parent.parent
_HOOK_DIR = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_HOOK_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOK_DIR))

from dotenv import load_dotenv

load_dotenv(_REPO_ROOT / ".env")

from hook_constants import UNSTAKE_TO_ROOT_IF_PRICE_ABOVE, MIN_STAKE_RAO
from act import move_stake_to_root, move_stake_to_root_if_price
from app.core.config import settings
from app.services.stake_service import get_stake_custom
from app.globals import init_globals



if __name__ == "__main__":
    subtensor = bt.Subtensor("finney")
    init_globals()  # Pre-initialize globals to avoid first-call delay

    while True:
        staked = False
        for netuid, ref_price in UNSTAKE_TO_ROOT_IF_PRICE_ABOVE.items():
            stake_balance = get_stake_custom(subtensor, settings.REAL_ACCOUNT_SS58, settings.DEFAULT_DEST_HOTKEY, netuid)
            if stake_balance.rao >= MIN_STAKE_RAO:
                staked = True
                break
        if staked:
            break
        print("not staked")
        subtensor.wait_for_block()

    print("staked")
    while True:
        time.sleep(8)
        for netuid, ref_price in UNSTAKE_TO_ROOT_IF_PRICE_ABOVE.items():
            stake_balance = get_stake_custom(subtensor, settings.REAL_ACCOUNT_SS58, settings.DEFAULT_DEST_HOTKEY, netuid)
            if stake_balance.rao < MIN_STAKE_RAO:
                print(f"stake_balance is below MIN_STAKE_RAO for subnet {netuid}")
                continue
            
            move_stake_to_root_if_price(origin_netuid=netuid, ref_price_tao_per_alpha=ref_price, require_above=True, amount_tao=float(stake_balance.tao - 1))

