import os
import sys
from collections import deque
from pathlib import Path

import bittensor as bt
import time

_HOOK_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _HOOK_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_HOOK_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOK_DIR))

from event_watch import fetch_extrinsic_data, get_owner_coldkeys
from act import add_stake, add_stake_if_price
from hook_constants import (
    SEEN_MAX, 
    EXTRINSIC_START_CALL, 
    EXTRINSIC_SUBMIT_ENCRYPTED, 
    WHITELISTED_SUBNETS, 
    STAKE_AMOUNT_TAO, 
    BLACK_LISTED_COLDKEYS)
from app.globals import init_globals


def process_event(event: dict):
    event_type = event.get('event_type')
    subnet = event.get('subnet')
    address = event.get('address')
    if subnet not in WHITELISTED_SUBNETS:
        return
    
    if address in BLACK_LISTED_COLDKEYS:
        return
    
    if event_type == EXTRINSIC_START_CALL or event_type == EXTRINSIC_SUBMIT_ENCRYPTED:
        #If the price is below 0.015, stake 200 TAO
        add_stake_if_price(subnet, ref_price_tao_per_alpha=0.015, require_above=False, amount_tao=STAKE_AMOUNT_TAO)



if __name__ == "__main__":
    init_globals()  # Pre-initialize globals to avoid first-call delay
    subtensor = bt.Subtensor("finney")
    seen_order: deque = deque(maxlen=SEEN_MAX)
    seen_set: set = set()
    last_checked_block = 0
    print("Starting hook...")

    while True:
        current_block = subtensor.get_current_block()
        if current_block > last_checked_block:
            owner_coldkeys = get_owner_coldkeys(subtensor)
            last_checked_block = current_block
        events = fetch_extrinsic_data(subtensor, owner_coldkeys, seen_order, seen_set)
        if events:
            for event in events:
                process_event(event)
