import os
import csv
import time
import base64
import logging
import datetime
from datetime import date
from urllib.parse import urlparse, parse_qs

import pytz
import pyotp
import requests
from fyers_apiv3 import fyersModel

SERVER_URL = os.environ["SIGNAL_SERVER_URL"].rstrip("/")
API_KEY    = os.environ["SIGNAL_API_KEY"]

CLIENT_ID    = os.environ["FY_CLIENT_ID"]
SECRET_KEY   = os.environ["FY_SECRET_KEY"]
REDIRECT_URI = os.environ["FY_REDIRECT_URI"]
FY_ID        = os.environ["FY_ID"]
TOTP_KEY     = os.environ["FY_TOTP_KEY"]
PIN          = os.environ["FY_PIN"]

PAPER_TRADE  = os.environ.get("PAPER_TRADE", "false").lower() == "true"
TICK_SIZE    = 0.05
POLL_SEC     = 15
POSITION_POLL_SEC = 2

IST = pytz.timezone("Asia/Kolkata")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    datefmt="%H:%M:%S", handlers=[logging.StreamHandler(),
                                                  logging.FileHandler("client.log")])
log = logging.getLogger(__name__)

HEADERS = {"X-API-Key": API_KEY}


def _b64(v):
    return base64.b64encode(str(v).encode("ascii")).decode("ascii")


def login():
    VAG = "https://api-t2.fyers.in/vagator/v2"
    TOK = "https://api-t1.fyers.in/api/v3/token"
    r1 = requests.post(VAG + "/send_login_otp_v2",
                       json={"fy_id": _b64(FY_ID), "app_id": "2"}).json()
    if datetime.datetime.now().second % 30 > 27:
        time.sleep(3)
    r2 = requests.post(VAG + "/verify_otp",
                       json={"request_key": r1["request_key"],
                             "otp": pyotp.TOTP(TOTP_KEY).now()}).json()
    r3 = requests.post(VAG + "/verify_pin_v2",
                       json={"request_key": r2["request_key"],
                             "identity_type": "pin", "identifier": _b64(PIN)}).json()
    login_token = r3["data"]["access_token"]
    app_id, app_type = CLIENT_ID.split("-")
    r4 = requests.post(TOK, headers={"authorization": "Bearer " + login_token},
                       json={"fyers_id": FY_ID, "app_id": app_id,
                             "redirect_uri": REDIRECT_URI, "appType": app_type,
                             "code_challenge": "", "state": "s", "scope": "",
                             "nonce": "", "response_type": "code",
                             "create_cookie": True}).json()
    auth_code = parse_qs(urlparse(r4.get("Url") or r4.get("url")).query)["auth_code"][0]
    ses = fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY,
                                  redirect_uri=REDIRECT_URI, response_type="code",
                                  grant_type="authorization_code")
    ses.set_token(auth_code)
    token = ses.generate_token()["access_token"]
    fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=token, log_path="", is_async=False)
    log.info("Logged in: %s", fyers.get_profile().get("data", {}).get("name", ""))
    return fyers


def _tick(p):
    return round(round(p / TICK_SIZE) * TICK_SIZE, 2)


def _order(fyers, symbol, qty, otype, side, limit=0, stop=0):
    if PAPER_TRADE:
        log.info("[PAPER] side=%d type=%d %s qty=%d limit=%s stop=%s",
                 side, otype, symbol, qty, limit, stop)
        return "PAPER"
    data = {"symbol": symbol, "qty": qty, "type": otype, "side": side,
            "productType": "INTRADAY", "limitPrice": limit, "stopPrice": stop,
            "validity": "DAY", "disclosedQty": 0, "offlineOrder": False}
    resp = fyers.place_order(data)
    if resp.get("s") != "ok":
        raise RuntimeError("order failed: %s" % resp)
    return resp["id"]


def buy_market(fyers, symbol, qty):
    return _order(fyers, symbol, qty, otype=2, side=1)


def sell_market(fyers, symbol, qty):
    return _order(fyers, symbol, qty, otype=2, side=-1)


def arm_legs(fyers, symbol, qty, target_price, sl_trigger):
    if PAPER_TRADE:
        return "PAPER_TP", "PAPER_SL"
    sl_id = _order(fyers, symbol, qty, otype=3, side=-1, stop=_tick(sl_trigger))
    tp_id = _order(fyers, symbol, qty, otype=1, side=-1, limit=_tick(target_price))
    log.info("Legs armed | TP @%.2f id=%s | SL @%.2f id=%s",
             _tick(target_price), tp_id, _tick(sl_trigger), sl_id)
    return tp_id, sl_id


def cancel(fyers, oid):
    if oid and not PAPER_TRADE:
        try:
            fyers.cancel_order({"id": oid})
        except Exception as e:
            log.warning("cancel %s failed: %s", oid, e)


def get_ltp(fyers, symbol):
    resp = fyers.quotes({"symbols": symbol})
    return float(resp["d"][0]["v"]["lp"]) if resp.get("s") == "ok" else 0.0


def order_states(fyers, ids):
    out = {}
    if PAPER_TRADE:
        return out
    resp = fyers.orderbook()
    if resp.get("s") == "ok":
        for o in resp.get("orderBook", []):
            if o.get("id") in ids:
                out[o["id"]] = (o.get("status"), float(o.get("tradedPrice", 0) or 0))
    return out


LOG_FILE = "trades_log.csv"


def log_trade(row):
    new = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["date", "time", "symbol", "side", "entry", "exit", "qty", "pnl", "reason"])
        w.writerow(row)


def ask_signal():
    return requests.get(SERVER_URL + "/signal", headers=HEADERS, timeout=10).json()


def report_open(sig):
    requests.post(SERVER_URL + "/position/open", headers=HEADERS,
                  json={"symbol": sig["symbol"], "signal_candle": sig["signal_candle"]},
                  timeout=10)


def ask_position():
    return requests.get(SERVER_URL + "/position/check", headers=HEADERS, timeout=10).json()


def report_close():
    requests.post(SERVER_URL + "/position/close", headers=HEADERS, timeout=10)


def run_position(fyers, sig, entry_price):
    symbol, qty = sig["symbol"], sig["qty"]
    target_price = entry_price + sig["target_pts"]
    sl_trigger   = entry_price - sig["sl_pts"]
    time.sleep(1)
    tp_id, sl_id = arm_legs(fyers, symbol, qty, target_price, sl_trigger)

    while True:
        try:
            states = order_states(fyers, {tp_id, sl_id})
            tp_st, tp_px = states.get(tp_id, (None, 0.0))
            sl_st, sl_px = states.get(sl_id, (None, 0.0))
            if tp_st == 2:
                cancel(fyers, sl_id)
                return tp_px or target_price, "TARGET"
            if sl_st == 2:
                cancel(fyers, tp_id)
                return sl_px or sl_trigger, "STOPLOSS"

            resp = ask_position()
            if resp.get("action") == "EXIT":
                cancel(fyers, tp_id)
                cancel(fyers, sl_id)
                ltp = get_ltp(fyers, symbol)
                sell_market(fyers, symbol, qty)
                return ltp, resp.get("reason", "SERVER_EXIT")
        except Exception as e:
            log.warning("monitor error: %s", e)
        time.sleep(POSITION_POLL_SEC)


def main():
    fyers = login()
    last_candle = None
    log.info("Client started | PAPER_TRADE=%s | server=%s", PAPER_TRADE, SERVER_URL)

    while True:
        try:
            now = datetime.datetime.now(IST).strftime("%H:%M")
            if not ("09:15" <= now <= "15:30"):
                time.sleep(60); continue

            sig = ask_signal()
            if sig.get("action") != "ENTER":
                time.sleep(POLL_SEC); continue

            if sig["signal_candle"] == last_candle:
                time.sleep(POLL_SEC); continue
            last_candle = sig["signal_candle"]

            entry_price = get_ltp(fyers, sig["symbol"])
            log.info("ENTER %s %s qty=%d @%.2f", sig["side"], sig["symbol"], sig["qty"], entry_price)
            buy_market(fyers, sig["symbol"], sig["qty"])
            report_open(sig)

            exit_price, reason = run_position(fyers, sig, entry_price)
            pnl = round((exit_price - entry_price) * sig["qty"], 2)
            log.info("EXIT %s @%.2f pnl=%.2f (%s)", sig["symbol"], exit_price, pnl, reason)
            log_trade([date.today(), now, sig["symbol"], sig["side"],
                       entry_price, exit_price, sig["qty"], pnl, reason])
            report_close()

        except KeyboardInterrupt:
            log.info("stopped by user"); break
        except Exception as e:
            log.error("loop error: %s — retry 30s", e); time.sleep(30)


if __name__ == "__main__":
    main()
