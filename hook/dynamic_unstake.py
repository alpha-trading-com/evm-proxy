import bittensor as bt
import time
from hook_constants import UNSTAKE_TO_ROOT_IF_PRICE_ABOVE, MIN_STAKE_RAO
from act import move_stake_to_root, move_stake_to_root_if_price
from app.core.config import settings
from app.services.stake_service import get_stake_custom



if __name__ == "__main__":
    subtensor = bt.Subtensor("finney")
    subtensor.wait_for_block()

    while True:
        time.sleep(8)
        for netuid, ref_price in UNSTAKE_TO_ROOT_IF_PRICE_ABOVE.items():
            stake_balance = get_stake_custom(subtensor, settings.REAL_ACCOUNT_SS58, settings.DEFAULT_DEST_HOTKEY, netuid)
            if stake_balance.rao < MIN_STAKE_RAO:
                print(f"stake_balance is below MIN_STAKE_RAO for subnet {netuid}")
                continue
            
            move_stake_to_root_if_price(origin_netuid=netuid, ref_price_tao_per_alpha=ref_price, require_above=True, amount_tao=float(stake_balance.tao - 1))

