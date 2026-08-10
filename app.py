from __future__ import annotations

import datetime as dt
import os
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import pytz
from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel

import market_data as md
import strategy

IST = pytz.timezone("Asia/Kolkata")

INDEX = "SENSEX"
ENTRY_START = "09:20"
ENTRY_END = "14:30"
SQUARE_OFF = "15:15"


def _load_api_keys() -> dict[str, str]:
    raw = os.environ.get("CUSTOMER_KEYS", "demo-key:tester")
    return dict(pair.split(":", 1) for pair in raw.split(",") if pair)


API_KEYS = _load_api_keys()


class Action(str, Enum):
    WAIT = "WAIT"
    ENTER = "ENTER"
    HOLD = "HOLD"
    EXIT = "EXIT"
    NONE = "NONE"


class OpenPositionRequest(BaseModel):
    symbol: str
    signal_candle: Optional[str] = None


@dataclass
class OpenPosition:
    symbol: str
    entry_candle: Optional[str]


@dataclass
class Session:
    last_candle: Optional[str] = None
    open: Optional[OpenPosition] = None


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def get(self, api_key: str) -> Session:
        with self._lock:
            return self._sessions.setdefault(api_key, Session())


app = FastAPI(title="GG Signal Server")

FYERS = md.login()
sessions = SessionStore()


def get_session(x_api_key: str = Header(None)) -> Session:
    if not x_api_key or x_api_key not in API_KEYS:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid api key")
    return sessions.get(x_api_key)


def _now_hhmm() -> str:
    return dt.datetime.now(IST).strftime("%H:%M")


def _within_entry_window() -> bool:
    return ENTRY_START <= _now_hhmm() <= ENTRY_END


@app.get("/signal")
def signal(session: Session = Depends(get_session)) -> dict:
    if session.open:
        return {"action": Action.WAIT, "note": "position already open"}
    if not _within_entry_window():
        return {"action": Action.WAIT, "note": "outside entry window"}

    df5 = md.fetch_candles(FYERS, md.INDEX_SYMBOL[INDEX], interval="5")
    direction = strategy.index_direction(df5)
    if direction not in ("BUY_CE", "BUY_PE"):
        return {"action": Action.WAIT, "note": "no index direction"}
    opt_type = "CE" if direction == "BUY_CE" else "PE"

    spot = md.get_ltp(FYERS, md.INDEX_SYMBOL[INDEX])
    symbol, strike = md.atm_option_symbol(FYERS, INDEX, opt_type, spot)
    df1 = md.fetch_candles(FYERS, symbol, interval="1")
    is_buy, closed_iso = strategy.option_fresh_flip_up(df1, session.last_candle)
    session.last_candle = closed_iso
    if not is_buy:
        return {"action": Action.WAIT, "note": "waiting for option flip"}

    return {
        "action": Action.ENTER,
        "side": opt_type,
        "symbol": symbol,
        "strike": strike,
        "qty": md.LOT_SIZE[INDEX] * md.LOTS_PER_TRADE[INDEX],
        "target_pts": strategy.TARGET_POINTS[INDEX],
        "sl_pts": strategy.SL_POINTS[INDEX],
        "signal_candle": closed_iso,
    }


@app.post("/position/open")
def position_open(
    payload: OpenPositionRequest,
    session: Session = Depends(get_session),
) -> dict:
    session.open = OpenPosition(
        symbol=payload.symbol,
        entry_candle=payload.signal_candle,
    )
    return {"ok": True}


@app.get("/position/check")
def position_check(session: Session = Depends(get_session)) -> dict:
    pos = session.open
    if not pos:
        return {"action": Action.NONE}

    if _now_hhmm() >= SQUARE_OFF:
        return {"action": Action.EXIT, "reason": "SQUAREOFF"}

    df1 = md.fetch_candles(FYERS, pos.symbol, interval="1")
    if strategy.option_flipped_down(df1, pos.entry_candle):
        return {"action": Action.EXIT, "reason": "OPT_FLIP"}
    return {"action": Action.HOLD}


@app.post("/position/close")
def position_close(session: Session = Depends(get_session)) -> dict:
    session.open = None
    session.last_candle = None
    return {"ok": True}
