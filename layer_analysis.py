import csv
from statistics import mean

FILE = "btc_data_features.csv"
HORIZON = 12
SLIPPAGE = 0.0005
COMMISSION = 0.0005

def load():
    with open(FILE, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def evaluate(rows, condition, name, threshold, direction):
    """direction: 'long' или 'short'"""
    total = 0
    wins = 0
    pct_sum = 0.0
    for i, row in enumerate(rows):
        if i + HORIZON >= len(rows):
            break
        try:
            if not condition(row):
                continue
            price_now = float(row["price"])
            price_future = float(rows[i + HORIZON]["price"])
            if direction == "long":
                entry = price_now * (1 + SLIPPAGE)
                exit_p = price_future * (1 - SLIPPAGE)
            else:
                entry = price_now * (1 - SLIPPAGE)
                exit_p = price_future * (1 + SLIPPAGE)
            gross = (exit_p - entry) / entry * 100
            if direction == "short":
                gross = -gross
            net = gross - COMMISSION * 2 * 100
            total += 1
            pct_sum += net
            if net > 0:
                wins += 1
        except Exception:
            continue
    if total == 0:
        return None
    winrate = wins / total * 100
    expectancy = pct_sum / total
    return (total, winrate, expectancy)

def run(rows, name, thresholds):
    print(f"\n=== {name} ===")
    for label, cond, direction in thresholds:
        r = evaluate(rows, cond, name, label, direction)
        if r:
            n, wr, exp = r
            print(f"  {label}: {n} сигналов | {wr:.1f}% | {exp:+.3f}%")

def main():
    rows = load()
    total = len(rows)
    split = int(total * 0.7)
    train = rows[:split]
    test = rows[split:]
    print(f"Всего: {total} | Train: {len(train)} | Test: {len(test)}")

    # Определения слоёв
    layers = {
        "vol24h > 3000": (lambda r: float(r["vol24h"]) > 3000, "long"),
        "vol24h > 5000": (lambda r: float(r["vol24h"]) > 5000, "long"),
        "vol24h > 8000": (lambda r: float(r["vol24h"]) > 8000, "long"),

        "funding > 0.00005": (lambda r: abs(float(r["funding"])) > 0.00005, "long"),
        "funding > 0.0001": (lambda r: abs(float(r["funding"])) > 0.0001, "long"),
        "funding > 0.00015": (lambda r: abs(float(r["funding"])) > 0.00015, "long"),

        "delta > 0": (lambda r: float(r["delta"]) > 0, "long"),
        "delta > 5": (lambda r: float(r["delta"]) > 5, "long"),
        "delta > 10": (lambda r: float(r["delta"]) > 10, "long"),
        "delta < -5": (lambda r: float(r["delta"]) < -5, "short"),


        "rsi < 25": (lambda r: float(r["rsi"]) < 25, "long"),
        "rsi < 30": (lambda r: float(r["rsi"]) < 30, "long"),
        "rsi < 35": (lambda r: float(r["rsi"]) < 35, "long"),
        "rsi > 65": (lambda r: float(r["rsi"]) > 65, "short"),
        "rsi > 70": (lambda r: float(r["rsi"]) > 70, "short"),
        "rsi > 75": (lambda r: float(r["rsi"]) > 75, "short"),

        "hour 0-8": (lambda r: 0 <= int(r["hour"]) < 8, "long"),
        "hour 8-16": (lambda r: 8 <= int(r["hour"]) < 16, "long"),
        "hour 16-24": (lambda r: 16 <= int(r["hour"]) < 24, "long"),

        "pc5 > 0.5%": (lambda r: float(r.get("price_change_5", 0)) > 0.5, "long"),
        "pc5 < -0.5%": (lambda r: float(r.get("price_change_5", 0)) < -0.5, "short"),
        "pc5 > 1%": (lambda r: float(r.get("price_change_5", 0)) > 1, "long"),
        "pc5 < -1%": (lambda r: float(r.get("price_change_5", 0)) < -1, "short"),

        "oi5 > 0.5%": (lambda r: float(r.get("oi_change_5", 0)) > 0.5, "long"),
        "oi5 > 1%": (lambda r: float(r.get("oi_change_5", 0)) > 1, "long"),
        "oi5 < -0.5%": (lambda r: float(r.get("oi_change_5", 0)) < -0.5, "short"),
    }

    # Группировка по слою
    groups = {}
    for label, (cond, direction) in layers.items():
        key = label.split()[0]
        if key not in groups:
            groups[key] = []
        groups[key].append((label, cond, direction))

    for group_name, thresholds in groups.items():
        print(f"\n--- {group_name} ---")
        for label, cond, direction in thresholds:
            r_train = evaluate(train, cond, label, label, direction)
            r_test = evaluate(test, cond, label, label, direction)
            line = f"  {label}: "
            if r_train:
                n, wr, exp = r_train
                line += f"train {n} | {wr:.1f}% | {exp:+.3f}% | "
            if r_test:
                n, wr, exp = r_test
                line += f"test {n} | {wr:.1f}% | {exp:+.3f}%"
            print(line)

if __name__ == "__main__":
    main()
