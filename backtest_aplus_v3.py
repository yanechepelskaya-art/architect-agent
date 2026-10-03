# backtest_aplus_v3.py — бэктест A+ (7/7, с Delta)
import csv

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    gains, losses = [], []
    for i in range(1, len(prices)):
        d = prices[i] - prices[i-1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
    if avg_l == 0:
        return 100
    rs = avg_g / avg_l
    return 100 - (100 / (1 + rs))

def calculate_atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return 0
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    atr = sum(trs[:period]) / period
    for i in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period
    return atr

def detect_phase(chg_15):
    if abs(chg_15) < 0.3:
        return "compression"
    elif chg_15 >= 0.8:
        return "emanation"
    elif chg_15 <= -0.8:
        return "flush"
    else:
        return "impulse"

def main():
    rows = []
    with open("btc_history_delta.csv", "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    print(f"Загружено: {len(rows)} строк")

    closes, highs, lows, ois, vols = [], [], [], [], []
    signals = []

    for i, row in enumerate(rows):
        try:
            close = float(row["close"])
            high = float(row["high"])
            low = float(row["low"])
            oi_usd = float(row["oi_usd"])
            vol_btc = float(row["vol"])
            delta_sum = float(row.get("delta_sum", 0))

            closes.append(close)
            highs.append(high)
            lows.append(low)
            ois.append(oi_usd)
            vols.append(vol_btc * close)

            if i < 30:
                continue

            rsi = calculate_rsi(closes)
            atr = calculate_atr(highs, lows, closes)
            vol_usdt = vols[-1]

            avg_vol_20 = sum(vols[-21:-1]) / max(1, len(vols[-21:-1]))
            oi_change = (ois[-1] - ois[-6]) / ois[-6] * 100 if len(ois) >= 6 and ois[-6] > 0 else 0

            price_15 = closes[i-15] if i >= 15 else closes[0]
            chg_15 = (close - price_15) / price_15 * 100
            phase = detect_phase(chg_15)
            hour = int(row["time"][11:13])

            # 7 слоёв
            layers = 0
            if oi_change > 0:
                layers += 1
            if vol_usdt > 2 * avg_vol_20:
                layers += 1
            if 30 < rsi < 70:
                layers += 1
            if atr > 1.2 * (sum([calculate_atr(highs[:j+1], lows[:j+1], closes[:j+1]) for j in range(max(0, i-20), i)]) / max(1, min(20, i))):
                layers += 1
            if phase in ("impulse", "emanation"):
                layers += 1
            if 8 <= hour <= 22:
                layers += 1
            # Delta — только если есть
            if delta_sum > 0:
                layers += 1

            # Порог — 4 из 7 (или 4 из 6, если Delta нет)
            if layers >= 4:
                future_1 = float(rows[i+1]["close"]) if i+1 < len(rows) else close
                future_4 = float(rows[i+4]["close"]) if i+4 < len(rows) else close
                future_24 = float(rows[i+24]["close"]) if i+24 < len(rows) else close

                signals.append({
                    "time": row["time"],
                    "close": close,
                    "layers": layers,
                    "chg_1": (future_1 - close) / close * 100,
                    "chg_4": (future_4 - close) / close * 100,
                    "chg_24": (future_24 - close) / close * 100,
                })
        except Exception:
            continue

    print(f"Сигналов: {len(signals)}")

    if not signals:
        print("Нет сигналов.")
        return

    n = len(signals)
    wins_1 = sum(1 for s in signals if s["chg_1"] > 0)
    wins_4 = sum(1 for s in signals if s["chg_4"] > 0)
    wins_24 = sum(1 for s in signals if s["chg_24"] > 0)
    avg_1 = sum(s["chg_1"] for s in signals) / n
    avg_4 = sum(s["chg_4"] for s in signals) / n
    avg_24 = sum(s["chg_24"] for s in signals) / n

    print()
    print("=== РЕЗУЛЬТАТЫ (v3 — 7 слоёв) ===")
    print(f"Всего сигналов: {n}")
    print()
    print(f"Через 1ч:  Winrate {wins_1/n*100:.1f}% ({wins_1}/{n}), средний {avg_1:+.2f}%")
    print(f"Через 4ч:  Winrate {wins_4/n*100:.1f}% ({wins_4}/{n}), средний {avg_4:+.2f}%")
    print(f"Через 24ч: Winrate {wins_24/n*100:.1f}% ({wins_24}/{n}), средний {avg_24:+.2f}%")

    with open("backtest_result_v3.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["time", "close", "layers", "chg_1", "chg_4", "chg_24"])
        for s in signals:
            w.writerow([s["time"], s["close"], s["layers"], s["chg_1"], s["chg_4"], s["chg_24"]])
    print()
    print("OK: backtest_result_v3.csv")

if __name__ == "__main__":
    main()
