import requests
import time
import csv
from datetime import datetime

# Интервал сбора (секунды)
INTERVAL = 60
# Файл для сохранения
FILE = "btc_data.csv"

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

def get_delta():
    d = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=5m&limit=2")
    if not d or "data" not in d:
        return None
    c = d["data"][0]
    o = float(c[1]); cl = float(c[4]); v = float(c[5])
    return v if cl >= o else -v

def init_file():
    try:
        with open(FILE, "x", newline="") as f:
            w = csv.writer(f)
            w.writerow(["time", "price", "vol24h", "high24h", "low24h", "oi", "funding", "delta"])
    except FileExistsError:
        pass

def collect():
    init_file()
    while True:
        t = get_ticker()
        if not t:
            time.sleep(INTERVAL)
            continue
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            t["price"], t["vol24h"], t["high24h"], t["low24h"],
            get_oi() or 0,
            get_funding() or 0,
            get_delta() or 0,
        ]
        with open(FILE, "a", newline="") as f:
            csv.writer(f).writerow(row)
        print(f"[{row[0]}] price={row[1]} oi={row[5]} fund={row[6]}")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    print("📊 Сбор данных запущен. Интервал: 60 сек.")
    collect()
