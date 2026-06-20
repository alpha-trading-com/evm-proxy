"""Pre-built add_stake: subnet 1, 200 TAO. prepare() at startup, on_event(event) when event fires."""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv

load_dotenv(_REPO_ROOT / ".env")

from app.core.config import settings
from app.globals import get_subtensor, get_w3_account_contract, init_globals
from app.services.extrinsics import add_stake_extrinsic
from evm.address import ss58_to_bytes32
from utils.substrate_runtime_call import runtime_call_bytes

NETUID = 1
AMOUNT_RAO = 200 * 10**9
GAS = 2_000_000

_prepared = None


def prepare():
    global _prepared
    init_globals()
    hotkey = settings.DEFAULT_DEST_HOTKEY
    subtensor = get_subtensor()
    call = add_stake_extrinsic(subtensor, hotkey, NETUID, AMOUNT_RAO)
    call_bytes = runtime_call_bytes(call)
    real_bytes = ss58_to_bytes32(settings.DELEGATOR_SS58.strip())
    w3, account, _, contract = get_w3_account_contract()
    _prepared = (w3, account, contract, real_bytes, call_bytes)
    print(f"prepared add_stake netuid={NETUID} amount_rao={AMOUNT_RAO}")


def on_event(event: dict) -> dict | None:
    if event.get("event_type") not in ("START_CALL", "SUBMIT_ENCRYPTED"):
        return None
    if _prepared is None:
        raise RuntimeError("call prepare() first")

    w3, account, contract, real_bytes, call_bytes = _prepared
    tx = contract.functions.proxyCall(real_bytes, 0, call_bytes).build_transaction(
        {
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address, "pending"),
            "gas": GAS,
            "gasPrice": w3.eth.gas_price,
        }
    )
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    h = tx_hash.hex() if hasattr(tx_hash, "hex") else str(tx_hash)
    print(f"submitted add_stake netuid={NETUID} tx_hash={h}")
    return {"ok": True, "tx_hash": h}


if __name__ == "__main__":
    prepare()
