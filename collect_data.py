import os
os.environ["HTTPS_PROXY"] = "socks5://127.0.0.1:10808"
os.environ["HTTP_PROXY"] = "socks5://127.0.0.1:10808"
import requests
import time
import csv
from datetime import datetime

# Интервал сбора (секунды)
INTERVAL = 60
# Файл для сохранения
FILE = "btc_data_v3.csv"

def okx_get(url):
    try:
        r = requests.get(url, timeout=10)
        return r.json()
    except:
        return None

def get_ticker():
    d = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
    if not d or "data" not in d:
        return None
    t = d["data"][0]
    return {
        "price": float(t["last"]),
        "vol24h": float(t["vol24h"]),
        "high24h": float(t["high24h"]),
        "low24h": float(t["low24h"]),
    }

def get_oi():
    d = okx_get("https://www.okx.com/api/v5/public/open-interest?instId=BTC-USDT-SWAP")
    if not d or "data" not in d:
        return None
    return float(d["data"][0]["oi"])

def get_funding():
    d = okx_get("https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP")
    if not d or "data" not in d:
        return None
    return float(d["data"][0]["fundingRate"])

def get_last_candle():
    """Тянет последнюю 1m-свечу: open, close."""
    d = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=1m&limit=1")
    if not d or "data" not in d or not d["data"]:
        return None
    c = d["data"][0]
    return {"open": float(c[1]), "close": float(c[4])}

def get_delta():
    d = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=5m&limit=2")
    if not d or "data" not in d:
        return None
    c = d["data"][0]
    o = float(c[1]); cl = float(c[4]); v = float(c[5])
    return v if cl >= o else -v

def get_cvd():
    d = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=1H&limit=24")
    if not d or "data" not in d:
        return None
    total = 0.0
    for c in d["data"]:
        o = float(c[1]); cl = float(c[4]); v = float(c[5])
        total += v if cl >= o else -v
    return total

def get_long_short():
    try:
        r = requests.get(
            "https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio?ccy=BTC&period=1H",
            timeout=10
        )
        data = r.json()
        if not data or data.get("code") != "0" or not data.get("data"):
            return None
        item = data["data"][0]
        ratio = float(item[1])
        if ratio <= 0:
            return None
        long_pct = ratio / (1 + ratio) * 100
        short_pct = 100 - long_pct
        return (round(long_pct, 2), round(short_pct, 2))
    except Exception:
        return None

def get_htf():
    try:
        d = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=1D&limit=30")
        if not d or "data" not in d:
            return (0, 0)
        candles = d["data"][::-1]
        if len(candles) < 7:
            return (0, 0)
        old_close = float(candles[-7][4])
        cur_close = float(candles[-1][4])
        pct = (cur_close - old_close) / old_close * 100
        if pct > 1:
            direction = 1
        elif pct < -1:
            direction = -1
        else:
            direction = 0
        strength = min(abs(pct) * 10, 100)
        return (direction, int(strength))
    except Exception:
        return (0, 0)

def get_ten():
    try:
        d = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=1H&limit=24")
        if not d or "data" not in d:
            return (0, 0)
        candles = d["data"]
        highs = [float(c[2]) for c in candles]
        lows = [float(c[3]) for c in candles]
        cur = float(candles[0][4])
        hi = max(highs)
        lo = min(lows)
        rng = hi - lo
        if rng == 0:
            return (0, 0)
        pos = (cur - lo) / rng
        if pos > 0.8:
            return (-1, 2)
        elif pos < 0.2:
            return (1, 2)
        else:
            return (0, 0)
    except Exception:
        return (0, 0)

def get_impulse():
    try:
        d = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=5m&limit=12")
        if not d or "data" not in d:
            return (0, 0)
        candles = d["data"]
        highs = [float(c[2]) for c in candles[1:]]
        lows = [float(c[3]) for c in candles[1:]]
        cur_close = float(candles[0][4])
        cur_vol = float(candles[0][5])
        avg_vol = sum(float(c[5]) for c in candles[1:]) / len(candles[1:])
        if avg_vol == 0:
            return (0, 0)
        vol_ratio = cur_vol / avg_vol
        if cur_close > max(highs) and vol_ratio > 1.5:
            return (1, int(min(vol_ratio * 50, 100)))
        elif cur_close < min(lows) and vol_ratio > 1.5:
            return (-1, int(min(vol_ratio * 50, 100)))
        else:
            return (0, 0)
    except Exception:
        return (0, 0)

def get_compass(htf_dir, htf_strength):
    try:
        d = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
        if not d or "data" not in d:
            return "E"
        t = d["data"][0]
        price = float(t["last"])
        open24 = float(t["open24h"])
        pct24 = (price - open24) / open24 * 100
        if htf_dir == 1 and pct24 > 0.5:
            return "N"
        elif htf_dir == 1 and pct24 < -0.5:
            return "E"
        elif htf_dir == -1 and pct24 < -0.5:
            return "S"
        elif htf_dir == -1 and pct24 > 0.5:
            return "W"
        else:
            return "E"
    except Exception:
        return "E"

def init_file():
    try:
        with open(FILE, "x", newline="") as f:
            w = csv.writer(f)
            w.writerow(["time", "price", "vol24h", "high24h", "low24h", "open", "close", "oi", "funding", "delta", "cvd_24h", "long_pct", "short_pct", "htf_dir", "htf_strength", "ten_dir", "ten_strength", "impulse", "impulse_ready", "compass"])
    except FileExistsError:
        pass

def collect():
    init_file()
    while True:
        t = get_ticker()
        if not t:
            time.sleep(INTERVAL)
            continue
        _ls = get_long_short()
        _long = _ls[0] if _ls else 0
        _short = _ls[1] if _ls else 0
        _htf = get_htf()
        _ten = get_ten()
        _imp = get_impulse()
        _comp = get_compass(_htf[0], _htf[1])
        _candle = get_last_candle()
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            t["price"], t["vol24h"], t["high24h"], t["low24h"],
            _candle.get("open", 0) if _candle else 0,
            _candle.get("close", 0) if _candle else 0,
            get_oi() or 0,
            get_funding() or 0,
            get_delta() or 0,
            get_cvd() or 0,
            _long,
            _short,
            _htf[0], _htf[1],
            _ten[0], _ten[1],
            _imp[0], _imp[1],
            _comp,
        ]
        with open(FILE, "a", newline="") as f:
            csv.writer(f).writerow(row)
        print(f"[{row[0]}] price={row[1]} oi={row[5]} fund={row[6]}")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    print("📊 Сбор данных запущен. Интервал: 60 сек.")
    collect()
