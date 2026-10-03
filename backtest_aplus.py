# backtest_aplus.py — бэктест A+ на истории
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
    with open("btc_history.csv", "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    print(f"Загружено: {len(rows)} строк")

    closes = []
    highs = []
    lows = []
    signals = []

    for i, row in enumerate(rows):
        try:
            close = float(row["close"])
            high = float(row["high"])
            low = float(row["low"])
            oi_usd = float(row["oi_usd"])
            vol_btc = float(row["vol"])

            closes.append(close)
            highs.append(high)
            lows.append(low)

            if i < 20:
                continue

            rsi = calculate_rsi(closes)
            atr = calculate_atr(highs, lows, closes)
            vol_usdt = vol_btc * close

            price_15 = closes[i-15] if i >= 15 else closes[0]
            chg_15 = (close - price_15) / price_15 * 100
            phase = detect_phase(chg_15)

            hour = int(row["time"][11:13])

            layers = 0
            if oi_usd > 0:
                layers += 1
            if vol_usdt > 500_000_000:
                layers += 1
            if rsi > 70 or rsi < 30:
                layers += 1
            if atr > 100:
                layers += 1
            if phase in ("compression", "impulse", "emanation", "flush"):
                layers += 1
            if 0 <= hour < 24:
                layers += 1

            if layers >= 5:
                if i + 24 >= len(closes):
                    continue
                future_1 = closes[i+1]
                future_4 = closes[i+4]
                future_24 = closes[i+24]

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
    print("=== РЕЗУЛЬТАТЫ ===")
    print(f"Всего сигналов: {n}")
    print()
    print(f"Через 1ч:  Winrate {wins_1/n*100:.1f}% ({wins_1}/{n}), средний {avg_1:+.2f}%")
    print(f"Через 4ч:  Winrate {wins_4/n*100:.1f}% ({wins_4}/{n}), средний {avg_4:+.2f}%")
    print(f"Через 24ч: Winrate {wins_24/n*100:.1f}% ({wins_24}/{n}), средний {avg_24:+.2f}%")

    with open("backtest_result.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["time", "close", "layers", "chg_1", "chg_4", "chg_24"])
        for s in signals:
            w.writerow([s["time"], s["close"], s["layers"], s["chg_1"], s["chg_4"], s["chg_24"]])
    print()
    print("OK: backtest_result.csv")

if __name__ == "__main__":
    main()
