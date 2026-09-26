import csv
from pathlib import Path

DATA_PATH = Path.home() / "Desktop" / "training_data_clean.csv"

COMMISSION = 0.001
SLIPPAGE = 0.0005
HORIZON = 30

def score_aplus(row):
    """Считает A+ по доступным слоям. Максимум 7."""
    score = 0
    details = []
    
    # OI change > 0.5
    try:
        oi = float(row.get("oi_change_5", 0))
        if oi > 0.5:
            score += 1; details.append("OI ✅")
        else:
            details.append("OI ❌")
    except:
        details.append("OI ❌")
    
    # Объём > 5000
    try:
        vol = float(row.get("vol24h", 0))
        if vol > 5000:
            score += 1; details.append("Объём ✅")
        else:
            details.append("Объём ❌")
    except:
        details.append("Объём ❌")
    
    # Дельта > 0
    try:
        d = float(row.get("delta", 0))
        if d > 0:
            score += 1; details.append("Дельта ✅")
        else:
            details.append("Дельта ❌")
    except:
        details.append("Дельта ❌")
    
    # RSI < 30 (перепроданность) или > 70 (перекупленность)
    try:
        rsi = float(row.get("rsi", 50))
        if rsi < 30 or rsi > 70:
            score += 1; details.append("RSI ✅")
        else:
            details.append("RSI ❌")
    except:
        details.append("RSI ❌")
    
    # ATR > 50 (волатильность)
    try:
        atr = float(row.get("atr", 0))
        if atr > 50:
            score += 1; details.append("ATR ✅")
        else:
            details.append("ATR ❌")
    except:
        details.append("ATR ❌")
    
    # Фаза emanation или flush
    phase = row.get("phase", "")
    if phase in ("emanation", "flush"):
        score += 1; details.append("Фаза ✅")
    else:
        details.append("Фаза ❌")
    
    # Час (Азия/Европа/Америка)
    try:
        h = int(row.get("hour", 0))
        if 8 <= h < 22:
            score += 1; details.append("Час ✅")
        else:
            details.append("Час ❌")
    except:
        details.append("Час ❌")
    
    return score, details

def backtest(rows, name):
    total = 0
    wins = 0
    losses = 0
    total_pct = 0.0
    scores = {}
    
    for i, row in enumerate(rows):
        if i + HORIZON >= len(rows):
            continue
        try:
            score, _ = score_aplus(row)
            if score < 6:
                continue
            price_now = float(row["price"])
            price_future = float(rows[i + HORIZON]["price"])
            entry = price_now * (1 + SLIPPAGE)
            exit_p = price_future * (1 - SLIPPAGE)
            gross_pct = (exit_p - entry) / entry * 100
            net_pct = gross_pct - COMMISSION * 2 * 100
            total += 1
            total_pct += net_pct
            if net_pct > 0: wins += 1
            else: losses += 1
            if score not in scores:
                scores[score] = {"n": 0, "w": 0, "pct": 0.0}
            scores[score]["n"] += 1
            scores[score]["pct"] += net_pct
            if net_pct > 0: scores[score]["w"] += 1
        except:
            continue
    
    if total > 0:
        wr = wins / total * 100
        avg = total_pct / total
        print(f"\n{name}: {total} сигналов | {wr:.1f}% | {avg:+.3f}%")
        print("  По score:")
        for s in sorted(scores.keys()):
            v = scores[s]
            wr_s = v["w"] / v["n"] * 100
            avg_s = v["pct"] / v["n"]
            print(f"    score {s}: {v['n']} | {wr_s:.1f}% | {avg_s:+.3f}%")

def main():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    
    total = len(rows)
    split = int(total * 0.7)
    train = rows[:split]
    test = rows[split:]
    
    print(f"Всего: {total} | Train: {len(train)} | Test: {len(test)}")
    backtest(train, "TRAIN")
    backtest(test, "TEST")

if __name__ == "__main__":
    main()
