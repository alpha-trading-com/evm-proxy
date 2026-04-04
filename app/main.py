"""
FastAPI app: EVM proxy stake / unstake / move stake.

Run from repo root:
  uvicorn app.main:app --host 0.0.0.0 --port 8000

Structure:
  app/
    main.py         – bootstrap, routers
    globals.py      – subtensor, w3/contract cache
    services/       – evm, stake, tolerance calc, stake_info
    routers/        – ui, stake, tolerance, stake_info, tolerance_offset
"""
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

from fastapi import FastAPI

from app.routers import ui, stake, tolerance, stake_info, tolerance_offset

app = FastAPI(title="StakeWrap Control", version="1.0.0")

app.include_router(ui.router)
app.include_router(stake.router)
app.include_router(tolerance.router)
app.include_router(stake_info.router)
app.include_router(tolerance_offset.router)
