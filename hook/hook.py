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
from act import add_stake
from hook_constants import SEEN_MAX, EXTRINSIC_START_CALL, EXTRINSIC_SUBMIT_ENCRYPTED, WHITELISTED_SUBNETS



if __name__ == "__main__":
    subtensor = bt.Subtensor("finney")
    seen_order: deque = deque(maxlen=SEEN_MAX)
    seen_set: set = set()
    last_checked_block = 0


    while True:
        current_block = subtensor.get_current_block()
        if current_block > last_checked_block:
            owner_coldkeys = get_owner_coldkeys(subtensor)
            last_checked_block = current_block
        events = fetch_extrinsic_data(subtensor, owner_coldkeys, seen_order, seen_set)
        if events:
            print(events)
            for event in events:
                event_type = event.get('event_type')
                if event_type == EXTRINSIC_START_CALL:
                    add_stake(event.get('subnet'))
                elif event_type == EXTRINSIC_SUBMIT_ENCRYPTED:
                    add_stake(event.get('subnet'))
        time.sleep(1)
