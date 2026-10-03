import csv
import datetime

def calculate_atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return 0
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        trs.append(tr)
    # Wilder's smoothing
    atr = sum(trs[:period]) / period
    for i in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period
    return atr

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    gains = []
    losses = []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i-1]
        if delta > 0:
            gains.append(delta)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(delta))
    # Wilder's smoothing
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

rows = []
with open("btc_data_v3.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)

print(f"Загружено {len(rows)} строк")

prices = []
highs = []
lows = []
features = []

for i, row in enumerate(rows):
    try:
        if "open" not in row or "close" not in row:
            continue
        price = float(row["price"])
        oi = float(row["oi"])
        prices.append(price)
        highs.append(float(row.get("high", price)))
        lows.append(float(row.get("low", price)))

        atr = calculate_atr(highs, lows, prices)
        rsi = calculate_rsi(prices)

        hour = datetime.datetime.fromisoformat(row["time"]).hour

        if i >= 5:
            price_change_5 = (float(rows[i]["price"]) - float(rows[i-5]["price"])) / float(rows[i-5]["price"]) * 100
            oi_prev = float(rows[i-5]["oi"])
            oi_change_5 = ((oi - oi_prev) / oi_prev * 100) if oi_prev > 0 else 0
        else:
            price_change_5 = 0
            oi_change_5 = 0

        features.append({
            **row,
            "atr": round(atr, 2),
            "rsi": round(rsi, 2),
            "hour": hour,
            "price_change_5": round(price_change_5, 4),
            "oi_change_5": round(oi_change_5, 4),
        })
    except Exception:
        continue

with open("btc_data_features.csv", "w", newline="") as f:
    fieldnames = [
        "time","price","vol24h","high24h","low24h","open","high","low","close",
        "oi","funding","delta","cvd_24h","long_pct","short_pct",
        "htf_dir","htf_strength","ten_dir","ten_strength",
        "impulse","impulse_ready","compass",
        "atr","rsi","hour","price_change_5","oi_change_5",
    ]
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(features)

print(f"✅ Сохранено {len(features)} строк → btc_data_features.csv")
print(f"📊 Новые фичи: atr, rsi, hour, price_change_5, oi_change_5")
