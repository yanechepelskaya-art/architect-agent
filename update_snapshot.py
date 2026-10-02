import csv
from datetime import datetime
from atr import get_atr_okx

INPUT = "btc_data_v3.csv"
OUTPUT = "training_data_snapshot.csv"

# ATR — теперь через atr.py (Уайлдер 14, OHLC OKX 1H).
# get_atr_okx() вызывается один раз в main() — ATR_VALUE.

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    gains, losses = [], []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i-1]
        if delta > 0:
            gains.append(delta); losses.append(0)
        else:
            gains.append(0); losses.append(abs(delta))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

def detect_phase(chg_15):
    if abs(chg_15) < 0.3:
        return "compression"
    elif chg_15 >= 0.8:
        return "emanation"
    elif chg_15 <= -0.8:
        return "flush"
    elif 0.3 <= abs(chg_15) < 0.8:
        return "impulse"
    return "flat"

def main():
    atr_value = get_atr_okx()
    print(f"ATR (OKX 1H): {atr_value}")
    rows = []
    with open(INPUT, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)

    if len(rows) < 20:
        print("Мало данных в btc_data_v3.csv:", len(rows))
        return

    out = []
    for i in range(15, len(rows)):
        r = rows[i]
        window = rows[max(0, i-20):i+1]

        try:
            prices = [float(x["price"]) for x in window]
            ois = [float(x["oi"]) for x in window]

            rsi = calculate_rsi(prices)
            atr = atr_value

            price_now = float(r["price"])
            price_5 = float(rows[i-5]["price"]) if i >= 5 else price_now
            price_change_5 = round((price_now - price_5) / price_5 * 100, 4)

            oi_now = float(r["oi"])
            oi_5 = float(rows[i-5]["oi"]) if i >= 5 else oi_now
            oi_change_5 = round((oi_now - oi_5) / oi_5 * 100, 4) if oi_5 else 0

            price_15 = float(rows[i-15]["price"]) if i >= 15 else prices[0]
            chg_15 = (price_now - price_15) / price_15 * 100 if price_15 else 0
            phase = detect_phase(chg_15)

            hour = int(r["time"][11:13])

            out.append({
                "time": r["time"],
                "price": r["price"],
                "vol24h": r["vol24h"],
                "high24h": r["high24h"],
                "low24h": r["low24h"],
                "oi": r["oi"],
                "funding": r["funding"],
                "delta": r["delta"],
                "atr": atr,
                "rsi": rsi,
                "hour": hour,
                "price_change_5": price_change_5,
                "oi_change_5": oi_change_5,
                "phase": phase,
            })
        except Exception as e:
            continue

    if not out:
        print("Не удалось собрать ни одной строки.")
        return

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "time","price","vol24h","high24h","low24h","oi","funding","delta",
            "atr","rsi","hour","price_change_5","oi_change_5","phase"
        ])
        w.writeheader()
        w.writerows(out)

    print(f"OK: {len(out)} строк записано в {OUTPUT}")
    print(f"Последняя: {out[-1]['time']} | phase={out[-1]['phase']} | rsi={out[-1]['rsi']}")

if __name__ == "__main__":
    main()
