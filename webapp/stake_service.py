"""Compose Subtensor calls and submit through DelegateProxyCaller (nested proxy aware)."""

from __future__ import annotations

import threading
from typing import Any, Optional, Tuple

import bittensor as bt
from bittensor import Balance
from eth_account import Account
from web3 import Web3
from web3.types import TxReceipt

from evm.delegate_proxy import get_contract, proxy_call_with_runtime_call
from evm.web3_provider import web3_legacy_ws
from utils.substrate_runtime_call import runtime_call_bytes

from webapp.config import WebSettings


class StakeService:
    """
    EVM signs ``proxyCall``; precompile ``real`` is ``evm_proxy_real_ss58`` (B).

    If ``stake_owner_ss58`` (A) differs from B, the runtime payload is
    ``Proxy::proxy(real=A, call=subtensor_call)`` so B forwards to A (proxy of proxy).
    """

    def __init__(self, settings: WebSettings):
        self._settings = settings
        self._lock = threading.Lock()
        self._st: Optional[bt.Subtensor] = None
        self._w3: Optional[Any] = None
        self._account: Optional[Account] = None
        self._contract = None

    def _ensure_web3(self) -> Tuple[Any, Account, Any]:
        if self._w3 is None or not self._w3.is_connected():
            self._w3 = web3_legacy_ws(self._settings.rpc_url)
        if self._account is None:
            self._account = Account.from_key(self._settings.private_key)
        if self._contract is None:
            addr = Web3.to_checksum_address(self._settings.contract_address)
            self._contract = get_contract(
                self._w3, addr, abi=self._settings.abi
            )
        return self._w3, self._account, self._contract

    def close(self) -> None:
        if self._st is not None:
            try:
                self._st.close()
            except Exception:
                pass
            self._st = None

    def _get_subtensor(self) -> bt.Subtensor:
        if self._st is None:
            self._st = bt.Subtensor(network=self._settings.subtensor_endpoint)
        return self._st

    def _wrap_for_owner(self, inner: Any) -> Any:
        s = self._settings
        if s.stake_owner_ss58.strip() == s.evm_proxy_real_ss58.strip():
            return inner
        sub = self._get_subtensor().substrate
        return sub.compose_call(
            call_module="Proxy",
            call_function="proxy",
            call_params={
                "real": s.stake_owner_ss58.strip(),
                "force_proxy_type": s.inner_proxy_type,
                "call": inner,
            },
        )

    def _submit(self, inner_call: Any) -> Tuple[bool, str, Optional[TxReceipt]]:
        payload = self._wrap_for_owner(inner_call)
        call_bytes = runtime_call_bytes(payload)
        w3, acct, c = self._ensure_web3()
        with self._lock:
            receipt = proxy_call_with_runtime_call(
                w3,
                acct,
                self._settings.contract_address,
                proxy_type=self._settings.precompile_proxy_type_uint8,
                runtime_call=call_bytes,
                real_ss58=self._settings.evm_proxy_real_ss58.strip(),
                contract=c,
            )
        ok = receipt.status == 1
        msg = "OK" if ok else f"EVM tx reverted (status={receipt.status})"
        return ok, msg, receipt

    def add_stake(
        self, netuid: int, hotkey: str, amount_tao: float
    ) -> Tuple[bool, str, Optional[TxReceipt]]:
        sub = self._get_subtensor().substrate
        amount = Balance.from_tao(amount_tao)
        inner = sub.compose_call(
            call_module="SubtensorModule",
            call_function="add_stake",
            call_params={
                "hotkey": hotkey.strip(),
                "netuid": netuid,
                "amount_staked": amount.rao,
            },
        )
        return self._submit(inner)

    def add_stake_limit(
        self,
        netuid: int,
        hotkey: str,
        amount_tao: float,
        limit_price_rao: int,
        allow_partial: bool = False,
    ) -> Tuple[bool, str, Optional[TxReceipt]]:
        sub = self._get_subtensor().substrate
        amount = Balance.from_tao(amount_tao)
        inner = sub.compose_call(
            call_module="SubtensorModule",
            call_function="add_stake_limit",
            call_params={
                "hotkey": hotkey.strip(),
                "netuid": netuid,
                "amount_staked": amount.rao,
                "limit_price": int(limit_price_rao),
                "allow_partial": allow_partial,
            },
        )
        return self._submit(inner)

    def remove_stake(
        self, netuid: int, hotkey: str, amount_tao: float
    ) -> Tuple[bool, str, Optional[TxReceipt]]:
        sub = self._get_subtensor().substrate
        amount = Balance.from_tao(amount_tao)
        inner = sub.compose_call(
            call_module="SubtensorModule",
            call_function="remove_stake",
            call_params={
                "hotkey": hotkey.strip(),
                "netuid": netuid,
                "amount_unstaked": max(0, int(amount.rao) - 1),
            },
        )
        return self._submit(inner)

    def remove_stake_limit(
        self,
        netuid: int,
        hotkey: str,
        amount_tao: float,
        limit_price_rao: int,
        allow_partial: bool = False,
    ) -> Tuple[bool, str, Optional[TxReceipt]]:
        sub = self._get_subtensor().substrate
        amount = Balance.from_tao(amount_tao)
        inner = sub.compose_call(
            call_module="SubtensorModule",
            call_function="remove_stake_limit",
            call_params={
                "hotkey": hotkey.strip(),
                "netuid": netuid,
                "amount_unstaked": max(0, int(amount.rao) - 1),
                "limit_price": int(limit_price_rao),
                "allow_partial": allow_partial,
            },
        )
        return self._submit(inner)

    def move_stake(
        self,
        origin_netuid: int,
        dest_netuid: int,
        origin_hotkey: str,
        dest_hotkey: str,
        amount_tao: float,
    ) -> Tuple[bool, str, Optional[TxReceipt]]:
        st = self._stake_balance_check(
            origin_hotkey, origin_netuid, amount_tao
        )
        if not st[0]:
            return False, st[1], None
        sub = self._get_subtensor().substrate
        amount = Balance.from_tao(amount_tao)
        inner = sub.compose_call(
            call_module="SubtensorModule",
            call_function="move_stake",
            call_params={
                "origin_hotkey": origin_hotkey.strip(),
                "destination_hotkey": dest_hotkey.strip(),
                "origin_netuid": origin_netuid,
                "destination_netuid": dest_netuid,
                "alpha_amount": max(0, int(amount.rao) - 1),
            },
        )
        return self._submit(inner)

    def _stake_balance_check(
        self, origin_hotkey: str, origin_netuid: int, amount_tao: float
    ) -> Tuple[bool, str]:
        subtensor = self._get_subtensor()
        bal = subtensor.get_stake(
            coldkey_ss58=self._settings.stake_owner_ss58.strip(),
            hotkey_ss58=origin_hotkey.strip(),
            netuid=origin_netuid,
        )
        want = Balance.from_tao(amount_tao)
        if want.rao > bal.rao:
            return False, f"Amount exceeds stake: have {bal}, requested {want}"
        return True, ""

    def burned_register(
        self, netuid: int, hotkey: str
    ) -> Tuple[bool, str, Optional[TxReceipt]]:
        sub = self._get_subtensor().substrate
        inner = sub.compose_call(
            call_module="SubtensorModule",
            call_function="burned_register",
            call_params={
                "netuid": netuid,
                "hotkey": hotkey.strip(),
            },
        )
        # Inner hop uses Registration; outer precompile type often still Any (0).
        s = self._settings
        if s.stake_owner_ss58.strip() != s.evm_proxy_real_ss58.strip():
            wrapped = sub.compose_call(
                call_module="Proxy",
                call_function="proxy",
                call_params={
                    "real": s.stake_owner_ss58.strip(),
                    "force_proxy_type": "Registration",
                    "call": inner,
                },
            )
            payload = wrapped
        else:
            payload = inner
        call_bytes = runtime_call_bytes(payload)
        w3, acct, c = self._ensure_web3()
        with self._lock:
            receipt = proxy_call_with_runtime_call(
                w3,
                acct,
                self._settings.contract_address,
                proxy_type=self._settings.precompile_proxy_type_uint8,
                runtime_call=call_bytes,
                real_ss58=self._settings.evm_proxy_real_ss58.strip(),
                contract=c,
            )
        ok = receipt.status == 1
        msg = "OK" if ok else f"EVM tx reverted (status={receipt.status})"
        return ok, msg, receipt
