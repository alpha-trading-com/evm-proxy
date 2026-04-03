"""Environment-driven settings for the web app."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from evm.contract import PROJECT_ROOT, load_deployment_info


@dataclass(frozen=True)
class WebSettings:
    rpc_url: str
    private_key: str
    contract_address: str
    abi: list | None
    subtensor_endpoint: str
    """SS58 passed to precompile as `real` (account that registered the EVM delegate)."""
    evm_proxy_real_ss58: str
    """Ultimate coldkey whose stake is changed; may equal evm_proxy_real_ss58."""
    stake_owner_ss58: str
    inner_proxy_type: str
    precompile_proxy_type_uint8: int


def load_web_settings() -> WebSettings:
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
    rpc = os.getenv("RPC_URL", "https://test.finney.opentensor.ai/").strip()
    pk = os.getenv("PRIVATE_KEY", "").strip()
    if not pk:
        raise RuntimeError("PRIVATE_KEY is required in the environment")

    dep = load_deployment_info()
    contract = dep["contract_address"].strip()
    abi = dep.get("abi")

    sub = os.getenv("SUBTENSOR_CHAIN_ENDPOINT", "").strip() or rpc

    # Back-compat: DELEGATE_SS58 was the precompile "real" in scripts
    real = (
        os.getenv("EVM_PROXY_REAL_SS58", "").strip()
        or os.getenv("DELEGATE_SS58", "").strip()
    )
    if not real:
        raise RuntimeError(
            "Set EVM_PROXY_REAL_SS58 (or DELEGATE_SS58): SS58 for precompile real = "
            "the Substrate account that added your EVM key as proxy."
        )

    owner = os.getenv("STAKE_OWNER_SS58", "").strip() or real

    inner_pt = os.getenv("PROXY_INNER_TYPE", "Staking").strip()
    pre_u8 = int(os.getenv("PRECOMPILE_PROXY_TYPE_UINT8", "0"))

    return WebSettings(
        rpc_url=rpc,
        private_key=pk,
        contract_address=contract,
        abi=abi,
        subtensor_endpoint=sub,
        evm_proxy_real_ss58=real,
        stake_owner_ss58=owner,
        inner_proxy_type=inner_pt,
        precompile_proxy_type_uint8=pre_u8,
    )
