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
from hook_constants import ROOT_NETUID, UNSTAKE_TO_ROOT_IF_PRICE_ABOVE, MIN_STAKE_RAO, NETWORK
from act import move_stake_to_root_if_price, move_stake_to_root
from app.globals import init_globals



if __name__ == "__main__":
    init_globals()  # Pre-initialize globals to avoid first-call delay
    subtensor = bt.Subtensor(NETWORK)

    staked_netuid = None

    while True:
        staked = False
        for netuid, ref_price in UNSTAKE_TO_ROOT_IF_PRICE_ABOVE.items():
            stake_balance = get_stake_custom(subtensor, settings.REAL_ACCOUNT_SS58, settings.DEFAULT_DEST_HOTKEY, netuid)
            if stake_balance.rao >= MIN_STAKE_RAO:
                staked = True
                staked_netuid = netuid
                break
        if staked:
            break
        print("not staked")
        subtensor.wait_for_block()

    print(f"staked_netuid: {staked_netuid}")
    ref_price = UNSTAKE_TO_ROOT_IF_PRICE_ABOVE[staked_netuid]

    while True:
        subnet_infos = subtensor.all_subnets()
        coldkey_ss58 = settings.REAL_ACCOUNT_SS58
        hotkey = settings.DEFAULT_DEST_HOTKEY
        all_subnets = subtensor.all_subnets()

        stake_balance = get_stake_custom(subtensor, coldkey_ss58, hotkey, staked_netuid)
        if stake_balance.rao < MIN_STAKE_RAO:
            print(f"stake_balance is below MIN_STAKE_RAO for subnet {staked_netuid}")
            continue

        subnet_price = float(all_subnets[staked_netuid].price.tao)
        
        if subnet_price >= ref_price:
            print(f"subnet_price is above ref_price for subnet {netuid}")
            move_stake_to_root(origin_netuid=staked_netuid, amount_tao=float(stake_balance.tao - 1))
            continue

