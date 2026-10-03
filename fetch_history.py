# fetch_history.py — загрузка истории с OKX
import requests
import csv
from datetime import datetime

# Параметры
OHLC_LIMIT = 300
OI_LIMIT = 720  # API даёт 720 часов
FUNDING_LIMIT = 300

def okx_get(url):
    try:
        r = requests.get(url, timeout=10)
        return r.json()
    except Exception as e:
        print(f"FAIL: {url} — {e}")
        return None

def fetch_ohlc():
    """OHLC 1H свечи."""
    d = okx_get(f"https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=1H&limit={OHLC_LIMIT}")
    if not d or "data" not in d:
        return {}
    out = {}
    for c in d["data"]:
        ts = int(c[0])
        out[ts] = {
            "open": float(c[1]),
            "high": float(c[2]),
            "low": float(c[3]),
            "close": float(c[4]),
            "vol": float(c[5]),
        }
    return out

def fetch_oi():
    """OI history."""
    d = okx_get(f"https://www.okx.com/api/v5/rubik/stat/contracts/open-interest-volume?ccy=BTC&period=1H")
    if not d or "data" not in d:
        return {}
    out = {}
    for row in d["data"]:
        ts = int(row[0])
        out[ts] = {"oi_usd": float(row[2])}
    return out

def fetch_funding():
    """Funding history."""
    d = okx_get(f"https://www.okx.com/api/v5/public/funding-rate-history?instId=BTC-USDT-SWAP&limit={FUNDING_LIMIT}")
    if not d or "data" not in d:
        return {}
    out = {}
    for row in d["data"]:
        ts = int(row["fundingTime"])
        out[ts] = {"funding": float(row["fundingRate"])}
    return out

def main():
    print("Загрузка OHLC...")
    ohlc = fetch_ohlc()
    print(f"  OHLC: {len(ohlc)}")

    print("Загрузка OI...")
    oi = fetch_oi()
    print(f"  OI: {len(oi)}")

    print("Загрузка Funding...")
    funding = fetch_funding()
    print(f"  Funding: {len(funding)}")

    # Объединяем по ts (OHLC — основа)
    rows = []
    for ts in sorted(ohlc.keys()):
        o = ohlc[ts]
        oi_val = oi.get(ts, {}).get("oi_usd", 0)
        # funding ближе всего к ts (в пределах часа)
        fund_val = 0
        for fts, fv in funding.items():
            if abs(fts - ts) < 3600000:
                fund_val = fv["funding"]
                break
        time_str = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M:%S")
        rows.append([
            time_str,
            o["open"], o["high"], o["low"], o["close"], o["vol"],
            oi_val, fund_val,
        ])

    with open("btc_history.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["time", "open", "high", "low", "close", "vol", "oi_usd", "funding"])
        w.writerows(rows)

    print(f"OK: btc_history.csv — {len(rows)} строк")

if __name__ == "__main__":
    main()
