import time
import logging
import csv
import os
import base64
import datetime
import threading
from datetime import date
from urllib.parse import urlparse, parse_qs

import pandas as pd
import numpy as np
import pytz
import pyotp
import requests

from fyers_apiv3 import fyersModel

CLIENT_ID    = "CWWW99PEX9-200"
SECRET_KEY   = "Lx9lc6rBHUNTY8hn"
REDIRECT_URI = "https://fyersapiapp.com/"

FY_ID    = "XG11294"
TOTP_KEY = "OCTCKYUOZ4ET2JXBF4XHSPTUI35QEP42"
PIN      = "1122"

GENERATE_TOKEN = True
TOKEN_FILE     = "fyers_token.txt"

PAPER_TRADE    = False
INSTRUMENTS    = ["SENSEX"]
LOT_SIZE       = {"SENSEX": 20}
LOTS_PER_TRADE = {"SENSEX": 10}

TARGET_POINTS  = {"SENSEX": 80}
SL_POINTS      = {"SENSEX": 40}

USE_EXCHANGE_SL_TP = True
TICK_SIZE          = 0.05

SQUARE_OFF_TIME  = "15:15"
ENTRY_START_TIME = "09:20"
ENTRY_END_TIME   = "14:30"

EMA_FAST = 9
EMA_SLOW = 21

MIN_INDEX_BARS  = EMA_SLOW + 2
MIN_OPTION_BARS = EMA_SLOW + 2

TF_INDEX  = "15"
TF_OPTION = "5"

POLL_INTERVAL_SEC     = 15
POSITION_CHECK_SEC    = 15

POSITION_POLL_SEC = 1

OPTION_FLIP_EXIT = False
OPTION_CHECK_SEC = 5

_log_lock = threading.Lock()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log"),
    ],
)
log = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")
_symbol_cache = {}

LOG_FILE = "trades_log.csv"

def init_log():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["date", "time", "instrument", "signal", "symbol",
                        "entry_price", "exit_price", "qty", "pnl", "exit_reason"])

def write_log(row):
    with _log_lock:
        with open(LOG_FILE, "a", newline="") as f:
            w = csv.writer(f)
            w.writerow([
                row.get("date"), row.get("time"), row.get("instrument"),
                row.get("signal"), row.get("symbol"), row.get("entry_price"),
                row.get("exit_price"), row.get("qty"), row.get("pnl"),
                row.get("exit_reason"),
            ])

def _b64(value):

    return base64.b64encode(str(value).encode("ascii")).decode("ascii")

def generate_access_token():

    if not FY_ID or not TOTP_KEY or not PIN or "YOUR_TOTP" in TOTP_KEY:
        raise ValueError(
            "TOTP login needs FY_ID, TOTP_KEY and PIN set at the top of the file.")

    VAGATOR   = "https://api-t2.fyers.in/vagator/v2"
    TOKEN_URL = "https://api-t1.fyers.in/api/v3/token"

    r1 = requests.post(VAGATOR + "/send_login_otp_v2",
                       json={"fy_id": _b64(FY_ID), "app_id": "2"}).json()
    if "request_key" not in r1:
        raise Exception("send_login_otp failed: " + str(r1))

    if datetime.datetime.now().second % 30 > 27:
        time.sleep(3)

    r2 = requests.post(VAGATOR + "/verify_otp",
                       json={"request_key": r1["request_key"],
                             "otp": pyotp.TOTP(TOTP_KEY).now()}).json()
    if "request_key" not in r2:
        raise Exception("verify_otp (TOTP) failed: " + str(r2))

    ses = requests.Session()
    r3 = ses.post(VAGATOR + "/verify_pin_v2",
                  json={"request_key": r2["request_key"],
                        "identity_type": "pin", "identifier": _b64(PIN)}).json()
    login_token = (r3.get("data") or {}).get("access_token")
    if not login_token:
        raise Exception("verify_pin failed: " + str(r3))

    app_id, app_type = CLIENT_ID.split("-")
    r4 = requests.post(
        TOKEN_URL,
        headers={"authorization": "Bearer " + login_token},
        json={
            "fyers_id":       FY_ID,
            "app_id":         app_id,
            "redirect_uri":   REDIRECT_URI,
            "appType":        app_type,
            "code_challenge": "",
            "state":          "sample",
            "scope":          "",
            "nonce":          "",
            "response_type":  "code",
            "create_cookie":  True,
        }).json()
    redirect = r4.get("Url") or r4.get("url")
    if not redirect:
        raise Exception("auth_code step failed: " + str(r4))
    auth_code = parse_qs(urlparse(redirect).query).get("auth_code", [None])[0]
    if not auth_code:
        raise Exception("could not extract auth_code from: " + redirect)

    session = fyersModel.SessionModel(
        client_id=CLIENT_ID,
        secret_key=SECRET_KEY,
        redirect_uri=REDIRECT_URI,
        response_type="code",
        grant_type="authorization_code",
    )
    session.set_token(auth_code)
    response = session.generate_token()
    if response.get("s") != "ok":
        raise Exception("Token generation failed: " + str(response))

    access_token = response["access_token"]
    with open(TOKEN_FILE, "w") as f:
        f.write(access_token)

    log.info("TOTP login successful — access token saved to %s", TOKEN_FILE)
    return access_token

def load_access_token():
    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError("Token file not found. Set GENERATE_TOKEN = True and run once.")
    with open(TOKEN_FILE) as f:
        token = f.read().strip()
    if not token:
        raise ValueError("Token file is empty. Set GENERATE_TOKEN = True.")
    return token

def login():
    if GENERATE_TOKEN:
        access_token = generate_access_token()
    else:
        access_token = load_access_token()

    fyers = fyersModel.FyersModel(
        client_id=CLIENT_ID,
        token=access_token,
        log_path="",
        is_async=False,
    )

    profile = fyers.get_profile()
    if profile.get("s") != "ok":
        raise Exception("Fyers login check failed: " + str(profile))

    log.info("Fyers login successful! User: %s", profile.get("data", {}).get("name", ""))
    return fyers

INDEX_SYMBOL = {
    "SENSEX": "BSE:SENSEX-INDEX",
}

EXCHANGE_PREFIX = {
    "SENSEX": "BSE:",
}

STRIKE_STEP = {
    "SENSEX": 100,
}

EXPIRY_WEEKDAY = {
    "SENSEX": 3,
}

MONTH_MAP = {
    1: "JAN", 2: "FEB",  3: "MAR", 4: "APR",
    5: "MAY", 6: "JUN",  7: "JUL", 8: "AUG",
    9: "SEP", 10: "OCT", 11: "NOV", 12: "DEC",
}

WEEKLY_MONTH_CODE = {
    1: "1", 2: "2", 3: "3", 4: "4",  5: "5",  6: "6",
    7: "7", 8: "8", 9: "9", 10: "O", 11: "N", 12: "D",
}

def next_expiry_day(d, weekday):

    return d + datetime.timedelta(days=(weekday - d.weekday()) % 7)

def is_last_expiry_day_of_month(d):

    return (d + datetime.timedelta(days=7)).month != d.month

def weekly_symbol(index, exp, strike, opt_type):

    return "{}{}{}{}{:02d}{}{}".format(
        EXCHANGE_PREFIX[index], index, exp.strftime("%y"),
        WEEKLY_MONTH_CODE[exp.month], exp.day, strike, opt_type)

def monthly_symbol(index, exp, strike, opt_type):

    return "{}{}{}{}{}{}".format(
        EXCHANGE_PREFIX[index], index, exp.strftime("%y"),
        MONTH_MAP[exp.month], strike, opt_type)

def get_atm_option_info(fyers, index, opt_type, spot):
    step   = STRIKE_STEP[index]
    strike = int(round(spot / step) * step)
    today  = date.today()

    cache_key = "{}_{}_{}".format(index, strike, opt_type)
    cached = _symbol_cache.get(cache_key)
    if cached and cached["date"] == today:
        return cached["info"]

    candidates = []

    wd  = EXPIRY_WEEKDAY[index]
    exp = next_expiry_day(today, wd)
    for k in range(3):
        e = exp + datetime.timedelta(days=7 * k)
        if is_last_expiry_day_of_month(e):
            candidates.append(monthly_symbol(index, e, strike, opt_type))
        else:
            candidates.append(weekly_symbol(index, e, strike, opt_type))

            candidates.append(weekly_symbol(
                index, e - datetime.timedelta(days=1), strike, opt_type))

    for months_ahead in range(0, 2):
        m = today.month + months_ahead
        y = today.year + (m - 1) // 12
        m = ((m - 1) % 12) + 1
        sym = monthly_symbol(index, date(y, m, 1), strike, opt_type)
        if sym not in candidates:
            candidates.append(sym)

    log.info("Trying %d candidate symbols for %s %s %s (nearest expiry first)",
             len(candidates), index, strike, opt_type)

    try:
        resp = fyers.quotes({"symbols": ",".join(candidates)})
        if resp.get("s") == "ok" and resp.get("d"):

            ltp_map = {}
            for item in resp["d"]:
                v   = item.get("v", {})
                ltp = float(v.get("lp", 0) or 0)
                sym = v.get("symbol", "")
                if ltp > 0 and sym:
                    ltp_map[sym] = ltp

            for sym in candidates:
                if sym in ltp_map:
                    log.info("Option symbol found: %s  LTP=%.2f", sym, ltp_map[sym])
                    info = {"symbol": sym, "strike": strike,
                            "expiry": "auto", "lot_size": LOT_SIZE[index]}
                    _symbol_cache[cache_key] = {"date": today, "info": info}
                    return info

        failed = candidates[:4]
        log.warning("All %d formats failed. Sample tried: %s", len(candidates), failed)
    except Exception as e:
        log.warning("Symbol quotes call failed: %s", e)

    symbol = monthly_symbol(index, today, strike, opt_type)
    log.warning("Using monthly fallback: %s", symbol)
    return {"symbol": symbol, "strike": strike,
            "expiry": "fallback", "lot_size": LOT_SIZE[index]}

def get_ltp(fyers, symbol):
    for attempt in range(2):
        resp = fyers.quotes({"symbols": symbol})
        if resp.get("s") == "ok":
            return float(resp["d"][0]["v"]["lp"])
        if resp.get("code") == 429:
            log.warning("Rate limit on LTP %s — waiting 5s before retry", symbol)
            time.sleep(5)
            continue
        raise Exception("LTP fetch failed for {}: {}".format(symbol, resp))
    raise Exception("LTP fetch failed after retry for {}".format(symbol))

def get_spot_ltp(fyers, index):
    return get_ltp(fyers, INDEX_SYMBOL[index])

def get_option_ltp(fyers, symbol):
    return get_ltp(fyers, symbol)

def fetch_candles(fyers, symbol, interval=TF_INDEX):
    now     = datetime.datetime.now(IST)
    from_dt = (now - datetime.timedelta(days=5)).replace(
        hour=9, minute=15, second=0, microsecond=0)

    data = {
        "symbol":      symbol,
        "resolution":  interval,
        "date_format": "0",
        "range_from":  str(int(from_dt.timestamp())),
        "range_to":    str(int(now.timestamp())),
        "cont_flag":   "1",
    }

    for attempt in range(2):
        resp = fyers.history(data)
        if resp.get("s") == "ok" and resp.get("candles"):
            raw = resp["candles"]
            if not raw:
                return pd.DataFrame()

            base_cols = ["epoch", "open", "high", "low", "close", "volume", "oi"]
            ncols = len(raw[0])
            if ncols <= len(base_cols):
                cols = base_cols[:ncols]
            else:
                cols = base_cols + ["extra{}".format(k) for k in range(ncols - len(base_cols))]
            df = pd.DataFrame(raw, columns=cols)
            df["date"] = pd.to_datetime(df["epoch"], unit="s", utc=True).dt.tz_convert(IST)
            df = df.set_index("date").drop(columns=["epoch"]).sort_index()
            df = df.apply(pd.to_numeric)
            return df
        if resp.get("code") == 429:
            log.warning("Rate limit on %s — waiting 5s before retry", symbol)
            time.sleep(5)
            continue
        log.warning("Candle fetch failed for %s: %s", symbol, resp)
        return pd.DataFrame()

    log.warning("Candle fetch failed after retry for %s", symbol)
    return pd.DataFrame()

def _ema_pair(df, fast=EMA_FAST, slow=EMA_SLOW):

    close = df["close"].astype(float)
    ema_f = close.ewm(span=fast, adjust=False).mean()
    ema_s = close.ewm(span=slow, adjust=False).mean()
    return ema_f, ema_s

def compute_signal(df):

    if len(df) < MIN_INDEX_BARS:
        return "WAIT"

    ema_f, ema_s = _ema_pair(df)

    i = -2 if len(df) >= 2 else -1
    f = ema_f.iloc[i]
    s = ema_s.iloc[i]

    if f > s:
        return "BUY_CE"
    if f < s:
        return "BUY_PE"
    return "WAIT"

def compute_option_signal(df, direction, last_seen_candle):

    if len(df) < MIN_OPTION_BARS:
        return "WAIT", last_seen_candle

    ema_f, ema_s = _ema_pair(df)

    i         = -2 if len(df) >= 2 else -1
    closed_ts = df.index[i]

    if last_seen_candle is not None and closed_ts <= last_seen_candle:
        return "WAIT", last_seen_candle

    now_up  = ema_f.iloc[i]   > ema_s.iloc[i]
    prev_up = ema_f.iloc[i-1] >= ema_s.iloc[i-1]

    if now_up and not prev_up:
        return "BUY", closed_ts

    return "WAIT", closed_ts

def option_flipped_down(fyers, pos):

    df = fetch_candles(fyers, pos.symbol, interval=TF_OPTION)
    if df is None or len(df) < MIN_OPTION_BARS:
        return False

    ema_f, ema_s = _ema_pair(df)

    i         = -2 if len(df) >= 2 else -1
    closed_ts = df.index[i]

    if pos.entry_candle_ts is not None and closed_ts <= pos.entry_candle_ts:
        return False

    return bool(ema_f.iloc[i] < ema_s.iloc[i])

def place_buy_order(fyers, symbol, qty):
    if PAPER_TRADE:
        log.info("[PAPER] BUY  %s  qty=%d", symbol, qty)
        return "PAPER_ORDER"

    order_data = {
        "symbol":       symbol,
        "qty":          qty,
        "type":         2,
        "side":         1,
        "productType":  "INTRADAY",
        "limitPrice":   0,
        "stopPrice":    0,
        "validity":     "DAY",
        "disclosedQty": 0,
        "offlineOrder": False,
    }
    resp = fyers.place_order(order_data)
    if resp.get("s") != "ok":
        raise Exception("Buy order failed: " + str(resp))
    order_id = resp["id"]
    log.info("BUY order placed id=%s symbol=%s qty=%d", order_id, symbol, qty)
    return order_id

def place_sell_order(fyers, symbol, qty):
    if PAPER_TRADE:
        log.info("[PAPER] SELL %s  qty=%d", symbol, qty)
        return

    order_data = {
        "symbol":       symbol,
        "qty":          qty,
        "type":         2,
        "side":         -1,
        "productType":  "INTRADAY",
        "limitPrice":   0,
        "stopPrice":    0,
        "validity":     "DAY",
        "disclosedQty": 0,
        "offlineOrder": False,
    }
    resp = fyers.place_order(order_data)
    if resp.get("s") != "ok":
        raise Exception("Sell order failed: " + str(resp))
    log.info("SELL order placed symbol=%s qty=%d", symbol, qty)

def round_tick(price):
    return round(round(price / TICK_SIZE) * TICK_SIZE, 2)

def place_target_order(fyers, symbol, qty, price):

    order_data = {
        "symbol":       symbol,
        "qty":          qty,
        "type":         1,
        "side":         -1,
        "productType":  "INTRADAY",
        "limitPrice":   round_tick(price),
        "stopPrice":    0,
        "validity":     "DAY",
        "disclosedQty": 0,
        "offlineOrder": False,
    }
    resp = fyers.place_order(order_data)
    if resp.get("s") != "ok":
        raise Exception("Target order failed: " + str(resp))
    log.info("TARGET leg placed id=%s %s LIMIT SELL @%.2f", resp["id"], symbol, round_tick(price))
    return resp["id"]

def place_stoploss_order(fyers, symbol, qty, trigger):

    order_data = {
        "symbol":       symbol,
        "qty":          qty,
        "type":         3,
        "side":         -1,
        "productType":  "INTRADAY",
        "limitPrice":   0,
        "stopPrice":    round_tick(trigger),
        "validity":     "DAY",
        "disclosedQty": 0,
        "offlineOrder": False,
    }
    resp = fyers.place_order(order_data)
    if resp.get("s") != "ok":
        raise Exception("Stoploss order failed: " + str(resp))
    log.info("SL leg placed id=%s %s SL-M SELL trg=%.2f", resp["id"], symbol, round_tick(trigger))
    return resp["id"]

def cancel_order_safe(fyers, order_id):
    if not order_id or PAPER_TRADE:
        return
    try:
        resp = fyers.cancel_order({"id": order_id})
        if resp.get("s") != "ok":
            log.warning("Cancel failed for order %s: %s", order_id, resp)
    except Exception as e:
        log.warning("Cancel error for order %s: %s", order_id, e)

def get_order_states(fyers, order_ids):

    out = {}
    try:
        resp = fyers.orderbook()
        if resp.get("s") == "ok":
            for o in resp.get("orderBook", []):
                oid = o.get("id")
                if oid in order_ids:
                    out[oid] = (o.get("status"),
                                float(o.get("tradedPrice", 0) or 0))
    except Exception as e:
        log.warning("Orderbook fetch failed: %s", e)
    return out

def ensure_flat(fyers, symbol):

    if PAPER_TRADE:
        return
    try:
        resp = fyers.positions()
        if resp.get("s") != "ok":
            return
        for p in resp.get("netPositions", []):
            if p.get("symbol") == symbol:
                net = int(p.get("netQty", 0) or 0)
                if net < 0:
                    log.warning("Accidental short %d on %s — covering at market", net, symbol)
                    place_buy_order(fyers, symbol, -net)
                elif net > 0:
                    log.warning("Residual long %d on %s — selling at market", net, symbol)
                    place_sell_order(fyers, symbol, net)
    except Exception as e:
        log.warning("ensure_flat error for %s: %s", symbol, e)

def attach_exchange_legs(fyers, pos):

    if PAPER_TRADE or not USE_EXCHANGE_SL_TP:
        return False
    tp_id = sl_id = None
    try:
        time.sleep(1)
        sl_id = place_stoploss_order(fyers, pos.symbol, pos.qty, pos.sl_price)
        tp_id = place_target_order(fyers, pos.symbol, pos.qty, pos.target_price)
        pos.sl_order_id = sl_id
        pos.tp_order_id = tp_id
        pos.mode        = "EXCHANGE"
        log.info("Exchange SL/TP armed | %s | SL-M @%.2f (id=%s) | TP @%.2f (id=%s)",
                 pos.symbol, pos.sl_price, sl_id, pos.target_price, tp_id)
        return True
    except Exception as e:
        log.warning("Could not arm exchange SL/TP for %s (%s) — using software SL/TP",
                    pos.symbol, e)
        for oid in (sl_id, tp_id):
            cancel_order_safe(fyers, oid)
        return False

def ist_now():
    return datetime.datetime.now(IST)

def ist_time_str():
    return ist_now().strftime("%H:%M")

def is_market_hours():
    t = ist_time_str()
    return "09:15" <= t <= "15:30"

def can_enter():
    t = ist_time_str()
    return ENTRY_START_TIME <= t <= ENTRY_END_TIME

def should_square_off():
    return ist_time_str() >= SQUARE_OFF_TIME

class Position:
    def __init__(self, instrument, signal, opt_info, entry_price, qty,
                 entry_candle_ts=None):
        self.instrument      = instrument
        self.signal          = signal
        self.symbol          = opt_info["symbol"]
        self.entry_price     = entry_price
        self.qty             = qty
        self.entry_time      = ist_now()
        self.entry_candle_ts = entry_candle_ts
        self.closed          = False
        self.exit_price      = None
        self.exit_reason     = None
        self.target_price    = round_tick(entry_price + TARGET_POINTS[instrument])
        self.sl_price        = round_tick(entry_price - SL_POINTS[instrument])
        self.entry_direction = "UP" if signal == "BUY_CE" else "DOWN"
        self.mode            = "SOFT"
        self.tp_order_id     = None
        self.sl_order_id     = None

        log.info(
            "LEVELS | %s | Entry=%.2f | Target=%.2f (+Rs%d) | SL=%.2f (-Rs%d) | Dir=%s",
            instrument, entry_price,
            self.target_price, TARGET_POINTS[instrument],
            self.sl_price,     SL_POINTS[instrument],
            self.entry_direction,
        )

    def pnl(self):
        if self.exit_price is None:
            return None
        return (self.exit_price - self.entry_price) * self.qty

    def check_exit(self, ltp):
        if ltp >= self.target_price:
            return "TARGET"
        if ltp <= self.sl_price:
            return "STOPLOSS"
        if should_square_off():
            return "SQUAREOFF"
        return None

def record_exit(inst, pos, exit_price, reason):

    pos.exit_price  = exit_price
    pos.exit_reason = reason
    pos.closed      = True
    pnl             = pos.pnl()
    log.info("EXIT | %s | %s | entry=%.2f exit=%.2f PnL=%.2f | %s",
             inst, pos.symbol, pos.entry_price, exit_price, pnl, reason)
    write_log({
        "date": date.today(), "time": ist_time_str(),
        "instrument": inst,   "signal": pos.signal,
        "symbol": pos.symbol, "entry_price": pos.entry_price,
        "exit_price": exit_price, "qty": pos.qty,
        "pnl": round(pnl, 2), "exit_reason": reason,
    })

def close_at_market(fyers, inst, pos, reason):

    if pos.mode == "EXCHANGE":
        cancel_order_safe(fyers, pos.tp_order_id)
        cancel_order_safe(fyers, pos.sl_order_id)
    ltp = get_option_ltp(fyers, pos.symbol)
    place_sell_order(fyers, pos.symbol, pos.qty)
    if pos.mode == "EXCHANGE":
        ensure_flat(fyers, pos.symbol)
    record_exit(inst, pos, ltp, reason)

def monitor_position(fyers, inst, pos):

    last_option_check = None

    def option_flip_due(loop_start):

        nonlocal last_option_check
        if not OPTION_FLIP_EXIT:
            return False
        if (last_option_check is not None and
                (loop_start - last_option_check).total_seconds() < OPTION_CHECK_SEC):
            return False
        last_option_check = loop_start
        try:
            if option_flipped_down(fyers, pos):
                log.info("Option EMA9 crossed BELOW EMA21 on %s (%s) — exiting",
                         inst, pos.symbol)
                return True
        except Exception as e:
            log.warning("Option flip check failed for %s: %s", inst, e)
        return False

    while not pos.closed:
        loop_start = ist_now()
        try:
            if pos.mode == "EXCHANGE":
                leg_ids = {pos.tp_order_id, pos.sl_order_id}
                states  = get_order_states(fyers, leg_ids)
                tp_st, tp_px = states.get(pos.tp_order_id, (None, 0.0))
                sl_st, sl_px = states.get(pos.sl_order_id, (None, 0.0))

                if tp_st == 2:
                    cancel_order_safe(fyers, pos.sl_order_id)
                    ensure_flat(fyers, pos.symbol)
                    record_exit(inst, pos, tp_px or pos.target_price, "TARGET")
                    return
                if sl_st == 2:
                    cancel_order_safe(fyers, pos.tp_order_id)
                    ensure_flat(fyers, pos.symbol)
                    record_exit(inst, pos, sl_px or pos.sl_price, "STOPLOSS")
                    return
                if tp_st in (1, 5) or sl_st in (1, 5):
                    log.warning("%s exchange leg lost (tp=%s sl=%s) — reverting "
                                "to software SL/TP", inst, tp_st, sl_st)
                    cancel_order_safe(fyers, pos.tp_order_id)
                    cancel_order_safe(fyers, pos.sl_order_id)
                    pos.mode = "SOFT"

                if pos.mode == "EXCHANGE":
                    reason = "SQUAREOFF" if should_square_off() else None
                    if not reason and option_flip_due(loop_start):
                        reason = "OPT_FLIP"
                    if reason:
                        close_at_market(fyers, inst, pos, reason)
                        return

            if pos.mode == "SOFT":
                ltp    = get_option_ltp(fyers, pos.symbol)
                reason = pos.check_exit(ltp)
                if not reason and option_flip_due(loop_start):
                    reason = "OPT_FLIP"
                if reason:
                    place_sell_order(fyers, pos.symbol, pos.qty)
                    record_exit(inst, pos, ltp, reason)
                    return

        except Exception as e:
            log.warning("Position monitor error for %s: %s", inst, e)

        elapsed = (ist_now() - loop_start).total_seconds()
        time.sleep(max(0, POSITION_POLL_SEC - elapsed))

def run_bot():
    init_log()
    fyers = login()

    active          = {}
    active_threads  = {}
    traded_today    = set()

    last_seen_opt = {inst: None for inst in INSTRUMENTS}

    log.info("Bot started | PAPER_TRADE=%s | OPTION_FLIP_EXIT=%s | Watching: %s",
             PAPER_TRADE, OPTION_FLIP_EXIT, INSTRUMENTS)

    while True:
        try:
            now_str = ist_time_str()
            now_dt  = ist_now()

            if not is_market_hours():
                log.info("Market closed (%s). Sleeping 60s...", now_str)
                traded_today.clear()
                last_seen_opt = {inst: None for inst in INSTRUMENTS}
                time.sleep(60)
                continue

            for inst, pos in list(active.items()):
                if pos.closed:
                    del active[inst]
                    active_threads.pop(inst, None)
                    last_seen_opt[inst] = None

            if can_enter():
                if active:
                    log.info("Skipping scan — %d position(s) still open: %s",
                             len(active), list(active.keys()))
                else:
                    for inst in INSTRUMENTS:
                        if inst in traded_today:
                            continue
                        try:

                            df_index = fetch_candles(fyers, INDEX_SYMBOL[inst], interval=TF_INDEX)
                            if df_index is None or len(df_index) < MIN_INDEX_BARS:
                                log.info("%s 15min: not enough candles (%d)",
                                         inst, len(df_index) if df_index is not None else 0)
                                continue

                            index_signal = compute_signal(df_index)
                            log.info("%s 15min index (EMA9 vs EMA21) → %s", inst, index_signal)

                            if index_signal not in ("BUY_CE", "BUY_PE"):
                                continue

                            opt_type = "CE" if index_signal == "BUY_CE" else "PE"

                            spot     = get_spot_ltp(fyers, inst)
                            opt_info = get_atm_option_info(fyers, inst, opt_type, spot)

                            df_opt = fetch_candles(fyers, opt_info["symbol"], interval=TF_OPTION)
                            if df_opt is None or len(df_opt) < MIN_OPTION_BARS:
                                log.info("%s 5min option: not enough candles (%d)",
                                         inst, len(df_opt) if df_opt is not None else 0)
                                continue

                            opt_direction = "UP" if index_signal == "BUY_CE" else "DOWN"
                            opt_signal, new_seen_ts = compute_option_signal(
                                df_opt, opt_direction, last_seen_opt[inst])

                            last_seen_opt[inst] = new_seen_ts

                            log.info("%s 5min option EMA9/21 cross (%s) → %s  [last_seen=%s]",
                                     inst, opt_info["symbol"], opt_signal,
                                     new_seen_ts.strftime("%H:%M") if new_seen_ts else "None")

                            if opt_signal != "BUY":
                                log.info("%s waiting for fresh 5min option EMA9/21 bullish cross...", inst)
                                continue

                            qty         = LOT_SIZE[inst] * LOTS_PER_TRADE[inst]
                            entry_price = get_option_ltp(fyers, opt_info["symbol"])

                            log.info("ENTRY | %s | %s | strike=%s | LTP=%.2f | qty=%d",
                                     inst, opt_info["symbol"], opt_info["strike"],
                                     entry_price, qty)

                            place_buy_order(fyers, opt_info["symbol"], qty)

                            pos              = Position(inst, index_signal, opt_info,
                                                        entry_price, qty, new_seen_ts)
                            active[inst]     = pos

                            attach_exchange_legs(fyers, pos)

                            t = threading.Thread(
                                target=monitor_position,
                                args=(fyers, inst, pos),
                                daemon=True,
                            )
                            active_threads[inst] = t
                            t.start()

                        except Exception as e:
                            log.error("Signal check error for %s: %s", inst, e)
                        time.sleep(2)

            if should_square_off():
                for inst, pos in list(active.items()):
                    if not pos.closed:
                        try:
                            close_at_market(fyers, inst, pos, "SQUAREOFF")
                            del active[inst]
                            active_threads.pop(inst, None)
                        except Exception as e:
                            log.error("Squareoff error for %s: %s", inst, e)
                traded_today.clear()
                last_seen_opt = {inst: None for inst in INSTRUMENTS}

            time.sleep(POLL_INTERVAL_SEC)

        except KeyboardInterrupt:
            log.info("Bot stopped by user.")
            break
        except Exception as e:
            log.error("Loop error: %s — retrying in 30s", e)
            time.sleep(30)

if __name__ == "__main__":
    run_bot()
