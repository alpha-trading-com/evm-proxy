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

from app.core.config import settings
from app.globals import get_subtensor
from app.services.stake_service import (
    do_move_stake,
    do_move_stake_if_price,
    get_stake_custom,
    resolve_move_stake_amount,
)
from hook_constants import ROOT_NETUID, UNSTAKE_TO_ROOT_IF_PRICE_ABOVE, MIN_STAKE_RAO
from act import move_stake_to_root_if_price, move_stake_to_root



if __name__ == "__main__":
    subtensor = bt.Subtensor("finney")
    #move_stake_to_root_if_price(origin_netuid=4, ref_price_tao_per_alpha=0.05, require_above=True, amount_tao=None)
    #move_stake_to_root_if_price(netuid=40, ref_price_tao_per_alpha=0.02, require_above=True, amount_tao=100000000)
    #check_unstake_to_root_if_price()
    # subtensor = bt.Subtensor("finney")
    # last_checked_block = 0

    while True:
        current_block = subtensor.get_current_block()
        subnet_infos = subtensor.all_subnets()
        subtensor = get_subtensor()
        coldkey_ss58 = settings.REAL_ACCOUNT_SS58
        hotkey = settings.DEFAULT_DEST_HOTKEY

        for netuid, ref_price in UNSTAKE_TO_ROOT_IF_PRICE_ABOVE.items():
            stake_balance = get_stake_custom(subtensor, coldkey_ss58, hotkey, netuid)
            if stake_balance.rao < MIN_STAKE_RAO:
                print(f"stake_balance is below MIN_STAKE_RAO for subnet {netuid}")
                continue

            subnet_price = float(subtensor.all_subnets()[netuid].price.tao)
            
            if subnet_price >= ref_price:
                print(f"subnet_price is above ref_price for subnet {netuid}")
                move_stake_to_root(origin_netuid=netuid, amount_tao=float(stake_balance.tao - 1))
                continue

        time.sleep(9)
        move_stake_to_root_if_price(origin_netuid=netuid, ref_price_tao_per_alpha=ref_price, require_above=True, amount_tao=float(stake_balance.tao - 1))

