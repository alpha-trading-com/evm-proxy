"""Uvicorn entry: stake / unstake UI for EVM → (nested) Proxy → Subtensor."""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from typing import Any, Optional

# Repo root on path when running `uvicorn webapp.main:app` from project root
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from webapp.config import WebSettings, load_web_settings
from webapp.stake_service import StakeService

_templates_dir = os.path.join(os.path.dirname(__file__), "templates")
_static_dir = os.path.join(os.path.dirname(__file__), "static")
templates = Jinja2Templates(directory=_templates_dir)

_service: Optional[StakeService] = None
_settings_cache: Optional[WebSettings] = None


def get_settings() -> WebSettings:
    global _settings_cache
    if _settings_cache is None:
        _settings_cache = load_web_settings()
    return _settings_cache


def get_service() -> StakeService:
    global _service
    if _service is None:
        _service = StakeService(get_settings())
    return _service


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _service, _settings_cache
    _settings_cache = None
    _service = None
    try:
        get_service()
        yield
    finally:
        if _service is not None:
            _service.close()
        _service = None
        _settings_cache = None


app = FastAPI(
    title="EVM proxy stake",
    lifespan=lifespan,
)

if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")


def _json_ok(
    success: bool, message: str, receipt: Any = None
) -> dict[str, Any]:
    out: dict[str, Any] = {"success": success, "message": message}
    if receipt is not None:
        th = getattr(receipt, "transactionHash", None)
        if th is not None:
            out["tx_hash"] = th.hex() if hasattr(th, "hex") else str(th)
    return out


class NetuidHotkeyAmount(BaseModel):
    netuid: int = Field(..., ge=0)
    hotkey: str = Field(..., min_length=1)
    amount_tao: float = Field(..., gt=0)


class AddStakeLimitBody(NetuidHotkeyAmount):
    limit_price_rao: int = Field(..., ge=0)
    allow_partial: bool = False


class RemoveStakeLimitBody(AddStakeLimitBody):
    pass


class MoveStakeBody(BaseModel):
    origin_netuid: int = Field(..., ge=0)
    dest_netuid: int = Field(..., ge=0)
    origin_hotkey: str = Field(..., min_length=1)
    dest_hotkey: str = Field(..., min_length=1)
    amount_tao: float = Field(..., gt=0)


class BurnedRegisterBody(BaseModel):
    netuid: int = Field(..., ge=0)
    hotkey: str = Field(..., min_length=1)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    try:
        s = get_settings()
    except Exception as e:
        return HTMLResponse(
            f"<pre>Config error: {e}</pre>",
            status_code=500,
        )
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "evm_proxy_real": s.evm_proxy_real_ss58,
            "stake_owner": s.stake_owner_ss58,
            "nested": s.stake_owner_ss58.strip()
            != s.evm_proxy_real_ss58.strip(),
        },
    )


@app.get("/api/config")
async def api_config():
    try:
        s = get_settings()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {
        "evm_proxy_real_ss58": s.evm_proxy_real_ss58,
        "stake_owner_ss58": s.stake_owner_ss58,
        "nested_proxy": s.stake_owner_ss58.strip()
        != s.evm_proxy_real_ss58.strip(),
        "inner_proxy_type": s.inner_proxy_type,
        "precompile_proxy_type_uint8": s.precompile_proxy_type_uint8,
    }


@app.post("/api/add-stake")
async def api_add_stake(body: NetuidHotkeyAmount):
    try:
        ok, msg, rec = get_service().add_stake(
            body.netuid, body.hotkey, body.amount_tao
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return JSONResponse(_json_ok(ok, msg, rec), status_code=200 if ok else 400)


@app.post("/api/add-stake-limit")
async def api_add_stake_limit(body: AddStakeLimitBody):
    try:
        ok, msg, rec = get_service().add_stake_limit(
            body.netuid,
            body.hotkey,
            body.amount_tao,
            body.limit_price_rao,
            body.allow_partial,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return JSONResponse(_json_ok(ok, msg, rec), status_code=200 if ok else 400)


@app.post("/api/remove-stake")
async def api_remove_stake(body: NetuidHotkeyAmount):
    try:
        ok, msg, rec = get_service().remove_stake(
            body.netuid, body.hotkey, body.amount_tao
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return JSONResponse(_json_ok(ok, msg, rec), status_code=200 if ok else 400)


@app.post("/api/remove-stake-limit")
async def api_remove_stake_limit(body: RemoveStakeLimitBody):
    try:
        ok, msg, rec = get_service().remove_stake_limit(
            body.netuid,
            body.hotkey,
            body.amount_tao,
            body.limit_price_rao,
            body.allow_partial,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return JSONResponse(_json_ok(ok, msg, rec), status_code=200 if ok else 400)


@app.post("/api/move-stake")
async def api_move_stake(body: MoveStakeBody):
    try:
        ok, msg, rec = get_service().move_stake(
            body.origin_netuid,
            body.dest_netuid,
            body.origin_hotkey,
            body.dest_hotkey,
            body.amount_tao,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return JSONResponse(_json_ok(ok, msg, rec), status_code=200 if ok else 400)


@app.post("/api/burned-register")
async def api_burned_register(body: BurnedRegisterBody):
    try:
        ok, msg, rec = get_service().burned_register(body.netuid, body.hotkey)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return JSONResponse(_json_ok(ok, msg, rec), status_code=200 if ok else 400)


@app.get("/health")
async def health():
    return {"status": "ok"}
