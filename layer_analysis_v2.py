import csv

FILE = "btc_data_features.csv"
SLIPPAGE = 0.0005
COMMISSION = 0.0005
HORIZONS = [3, 6, 12, 24]

def load():
    with open(FILE, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def evaluate(rows, condition, direction, horizon):
    total = 0
    wins = 0
    pct_sum = 0.0
    for i, row in enumerate(rows):
        if i + horizon >= len(rows):
            break
        try:
            if not condition(row):
                continue
            price_now = float(row["price"])
            price_future = float(rows[i + horizon]["price"])
            if direction == "long":
                entry = price_now * (1 + SLIPPAGE)
                exit_p = price_future * (1 - SLIPPAGE)
                gross = (exit_p - entry) / entry * 100
            else:
                entry = price_now * (1 - SLIPPAGE)
                exit_p = price_future * (1 + SLIPPAGE)
                gross = -((exit_p - entry) / entry * 100)
            net = gross - COMMISSION * 2 * 100
            total += 1
            pct_sum += net
            if net > 0:
                wins += 1
        except Exception:
            continue
    if total == 0:
        return None
    return (total, wins / total * 100, pct_sum / total)

def main():
    rows = load()
    total = len(rows)
    split = int(total * 0.7)
    train = rows[:split]
    test = rows[split:]
    print(f"Всего: {total} | Train: {len(train)} | Test: {len(test)}")

    def rsi(r): return float(r["rsi"])
    def delta(r): return float(r["delta"])
    def atr(r): return float(r["atr"])
    def vol(r): return float(r["vol24h"])
    def hour(r): return int(r["hour"])
    def oi5(r): return float(r.get("oi_change_5", 0))

    combos = [
        ("RSI<30 & Delta>0", lambda r: rsi(r) < 30 and delta(r) > 0, "long"),
        ("RSI<30 & Delta<0", lambda r: rsi(r) < 30 and delta(r) < 0, "short"),
        ("ATR>50 & Vol>5000", lambda r: atr(r) > 50 and vol(r) > 5000, "long"),
        ("RSI<30 & OI5>0.5", lambda r: rsi(r) < 30 and oi5(r) > 0.5, "long"),
        ("RSI>65 & Delta<0", lambda r: rsi(r) > 65 and delta(r) < 0, "short"),
        ("ATR>50 & RSI<30", lambda r: atr(r) > 50 and rsi(r) < 30, "long"),
        ("Hour16-24 & ATR>50", lambda r: 16 <= hour(r) < 24 and atr(r) > 50, "long"),
        ("Delta>10 & Vol>5000", lambda r: delta(r) > 10 and vol(r) > 5000, "long"),
        ("RSI<30 & Delta>0 & H16-24", lambda r: rsi(r) < 30 and delta(r) > 0 and 16 <= hour(r) < 24, "long"),
        ("ATR>50 & Vol>5000 & H16-24", lambda r: atr(r) > 50 and vol(r) > 5000 and 16 <= hour(r) < 24, "long"),
        ("RSI<30 & OI5>0.5 & Delta>0", lambda r: rsi(r) < 30 and oi5(r) > 0.5 and delta(r) > 0, "long"),
    ]

    for name, cond, direction in combos:
        print(f"\n=== {name} ({direction}) ===")
        for h in HORIZONS:
            rt = evaluate(train, cond, direction, h)
            rs = evaluate(test, cond, direction, h)
            line = f"  h={h}: "
            if rt:
                line += f"train {rt[0]} | {rt[1]:.1f}% | {rt[2]:+.3f}% | "
            else:
                line += "train - | "
            if rs:
                line += f"test {rs[0]} | {rs[1]:.1f}% | {rs[2]:+.3f}%"
            else:
                line += "test -"
            print(line)

if __name__ == "__main__":
    main()
