"""Pydantic request/response models for API bodies."""
from pydantic import BaseModel


class StakeBody(BaseModel):
    hotkey: str
    netuid: int
    amount_tao: float | None = None


class StakeLimitBody(BaseModel):
    hotkey: str
    netuid: int
    amount_tao: float | None = None
    rate_tolerance: float = 0.5
    use_min_tolerance: bool = False
    allow_partial: bool = False


class StakeIfPriceBody(BaseModel):
    """Stake (market or limit) only if subnet alpha price vs reference passes the check (EVM precompile gate)."""

    hotkey: str
    netuid: int
    amount_tao: float | None = None
    ref_price_tao_per_alpha: float
    require_above: bool = True
    not_limited: bool = True
    rate_tolerance: float = 0.5
    use_min_tolerance: bool = False
    allow_partial: bool = False


class RemoveStakeBody(BaseModel):
    hotkey: str
    netuid: int
    amount: float | None = None


class RemoveStakeLimitBody(BaseModel):
    hotkey: str
    netuid: int
    amount: float | None = None
    rate_tolerance: float = 0.5
    use_min_tolerance: bool = False
    allow_partial: bool = False


class RemoveStakeIfPriceBody(BaseModel):
    """Unstake (market or limit) only if alpha price vs reference passes the check."""

    hotkey: str
    netuid: int
    amount: float | None = None
    ref_price_tao_per_alpha: float
    require_above: bool = True
    not_limited: bool = True
    rate_tolerance: float = 0.5
    use_min_tolerance: bool = False
    allow_partial: bool = False


class MoveStakeBody(BaseModel):
    origin_hotkey: str
    destination_hotkey: str
    origin_netuid: int
    destination_netuid: int
    amount_tao: float | None = None

class CalcToleranceBody(BaseModel):
    tao_amount: float
    netuid: int
    operation: str = "stake"


class ToleranceOffsetBody(BaseModel):
    """Body for PUT /api/tolerance-offset."""
    tolerance_offset: float | str


