import os
import time
import base64
import datetime
from datetime import date
from urllib.parse import urlparse, parse_qs

import pytz
import pyotp
import requests
import pandas as pd
from fyers_apiv3 import fyersModel

IST = pytz.timezone("Asia/Kolkata")

CLIENT_ID    = os.environ["FY_SERVER_CLIENT_ID"]
SECRET_KEY   = os.environ["FY_SERVER_SECRET_KEY"]
REDIRECT_URI = os.environ["FY_SERVER_REDIRECT_URI"]
FY_ID        = os.environ["FY_SERVER_ID"]
TOTP_KEY     = os.environ["FY_SERVER_TOTP_KEY"]
PIN          = os.environ["FY_SERVER_PIN"]

INDEX_SYMBOL    = {"SENSEX": "BSE:SENSEX-INDEX"}
EXCHANGE_PREFIX = {"SENSEX": "BSE:"}
STRIKE_STEP     = {"SENSEX": 100}
EXPIRY_WEEKDAY  = {"SENSEX": 3}
LOT_SIZE        = {"SENSEX": 20}
LOTS_PER_TRADE  = {"SENSEX": 10}
MONTH_MAP = {1:"JAN",2:"FEB",3:"MAR",4:"APR",5:"MAY",6:"JUN",
             7:"JUL",8:"AUG",9:"SEP",10:"OCT",11:"NOV",12:"DEC"}
WEEKLY_CODE = {1:"1",2:"2",3:"3",4:"4",5:"5",6:"6",7:"7",8:"8",9:"9",
               10:"O",11:"N",12:"D"}

_symbol_cache = {}


def _b64(v):
    return base64.b64encode(str(v).encode("ascii")).decode("ascii")


def login():
    VAG = "https://api-t2.fyers.in/vagator/v2"
    TOK = "https://api-t1.fyers.in/api/v3/token"

    r1 = requests.post(VAG + "/send_login_otp_v2",
                       json={"fy_id": _b64(FY_ID), "app_id": "2"}).json()
    if "request_key" not in r1:
        raise RuntimeError("send_login_otp failed: %s" % r1)
    if datetime.datetime.now().second % 30 > 27:
        time.sleep(3)
    r2 = requests.post(VAG + "/verify_otp",
                       json={"request_key": r1["request_key"],
                             "otp": pyotp.TOTP(TOTP_KEY).now()}).json()
    if "request_key" not in r2:
        raise RuntimeError("verify_otp failed: %s" % r2)
    r3 = requests.post(VAG + "/verify_pin_v2",
                       json={"request_key": r2["request_key"],
                             "identity_type": "pin",
                             "identifier": _b64(PIN)}).json()
    login_token = (r3.get("data") or {}).get("access_token")
    if not login_token:
        raise RuntimeError("verify_pin failed: %s" % r3)

    app_id, app_type = CLIENT_ID.split("-")
    r4 = requests.post(TOK, headers={"authorization": "Bearer " + login_token},
                       json={"fyers_id": FY_ID, "app_id": app_id,
                             "redirect_uri": REDIRECT_URI, "appType": app_type,
                             "code_challenge": "", "state": "s", "scope": "",
                             "nonce": "", "response_type": "code",
                             "create_cookie": True}).json()
    redirect = r4.get("Url") or r4.get("url")
    auth_code = parse_qs(urlparse(redirect).query).get("auth_code", [None])[0]
    if not auth_code:
        raise RuntimeError("auth_code step failed: %s" % r4)

    ses = fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY,
                                  redirect_uri=REDIRECT_URI, response_type="code",
                                  grant_type="authorization_code")
    ses.set_token(auth_code)
    resp = ses.generate_token()
    if resp.get("s") != "ok":
        raise RuntimeError("token generation failed: %s" % resp)
    return fyersModel.FyersModel(client_id=CLIENT_ID, token=resp["access_token"],
                                 log_path="", is_async=False)


def fetch_candles(fyers, symbol, interval):
    now = datetime.datetime.now(IST)
    frm = (now - datetime.timedelta(days=5)).replace(hour=9, minute=15,
                                                      second=0, microsecond=0)
    data = {"symbol": symbol, "resolution": interval, "date_format": "0",
            "range_from": str(int(frm.timestamp())),
            "range_to": str(int(now.timestamp())), "cont_flag": "1"}
    for _ in range(2):
        resp = fyers.history(data)
        if resp.get("s") == "ok" and resp.get("candles"):
            raw = resp["candles"]
            base = ["epoch", "open", "high", "low", "close", "volume", "oi"]
            cols = base[:len(raw[0])] if len(raw[0]) <= len(base) else \
                   base + ["x%d" % k for k in range(len(raw[0]) - len(base))]
            df = pd.DataFrame(raw, columns=cols)
            df["date"] = pd.to_datetime(df["epoch"], unit="s", utc=True).dt.tz_convert(IST)
            return df.set_index("date").drop(columns=["epoch"]).sort_index().apply(pd.to_numeric)
        if resp.get("code") == 429:
            time.sleep(5); continue
        break
    return pd.DataFrame()


def get_ltp(fyers, symbol):
    resp = fyers.quotes({"symbols": symbol})
    if resp.get("s") == "ok":
        return float(resp["d"][0]["v"]["lp"])
    raise RuntimeError("LTP failed for %s: %s" % (symbol, resp))


def _next_expiry(d, wd):
    return d + datetime.timedelta(days=(wd - d.weekday()) % 7)


def _is_month_last(d):
    return (d + datetime.timedelta(days=7)).month != d.month


def _weekly(idx, e, strike, ot):
    return "%s%s%s%s%02d%d%s" % (EXCHANGE_PREFIX[idx], idx, e.strftime("%y"),
                                 WEEKLY_CODE[e.month], e.day, strike, ot)


def _monthly(idx, e, strike, ot):
    return "%s%s%s%s%d%s" % (EXCHANGE_PREFIX[idx], idx, e.strftime("%y"),
                             MONTH_MAP[e.month], strike, ot)


def atm_option_symbol(fyers, index, opt_type, spot):
    step   = STRIKE_STEP[index]
    strike = int(round(spot / step) * step)
    today  = date.today()
    key    = "%s_%s_%s" % (index, strike, opt_type)
    cached = _symbol_cache.get(key)
    if cached and cached["date"] == today:
        return cached["symbol"], strike

    cands, wd = [], EXPIRY_WEEKDAY[index]
    exp = _next_expiry(today, wd)
    for k in range(3):
        e = exp + datetime.timedelta(days=7 * k)
        if _is_month_last(e):
            cands.append(_monthly(index, e, strike, opt_type))
        else:
            cands.append(_weekly(index, e, strike, opt_type))
            cands.append(_weekly(index, e - datetime.timedelta(days=1), strike, opt_type))

    resp = fyers.quotes({"symbols": ",".join(cands)})
    if resp.get("s") == "ok" and resp.get("d"):
        ltp_map = {i["v"].get("symbol"): float(i["v"].get("lp", 0) or 0)
                   for i in resp["d"] if i.get("v")}
        for sym in cands:
            if ltp_map.get(sym, 0) > 0:
                _symbol_cache[key] = {"date": today, "symbol": sym}
                return sym, strike

    fallback = _monthly(index, today, strike, opt_type)
    return fallback, strike
