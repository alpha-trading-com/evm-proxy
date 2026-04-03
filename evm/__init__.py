"""
EVM helpers: address conversion, deployment loading, and DelegateProxyCaller helpers.
"""

from evm.address import (
    SS58_PREFIX,
    account_id_to_ss58,
    contract_address_bytes32,
    h160_to_account_id,
    h160_to_ss58,
    ss58_to_bytes32,
)
from evm.contract import (
    DEFAULT_DEPLOYMENT_PATH,
    PROJECT_ROOT,
    STAKE_WRAP_ARTIFACT_PATH,
    get_project_root,
    get_stake_wrap_abi,
    load_deployment,
    load_deployment_info,
    get_contract,
)
from utils.proxy_type_u8 import resolve_proxy_type_u8
from evm.delegate_proxy import (
    CONTRACT_ABI,
    proxy_call_with_runtime_call,
)

__all__ = [
    "SS58_PREFIX",
    "account_id_to_ss58",
    "contract_address_bytes32",
    "h160_to_account_id",
    "h160_to_ss58",
    "ss58_to_bytes32",
    "DEFAULT_DEPLOYMENT_PATH",
    "PROJECT_ROOT",
    "STAKE_WRAP_ARTIFACT_PATH",
    "get_project_root",
    "get_stake_wrap_abi",
    "load_deployment",
    "load_deployment_info",
    "get_contract",
    "CONTRACT_ABI",
    "proxy_call_with_runtime_call",
    "resolve_proxy_type_u8",
]
