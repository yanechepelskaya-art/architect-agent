import csv
from pathlib import Path

DATA_PATH = Path.home() / "Desktop" / "training_data_clean.csv"

COMMISSION = 0.001
SLIPPAGE = 0.0005
HORIZON = 30

def backtest(rows, filter_fn):
    wins = 0
    losses = 0
    total_pct = 0.0
    count = 0
    for i, row in enumerate(rows):
        if i + HORIZON >= len(rows):
            continue
        try:
            if not filter_fn(row):
                continue
            price_now = float(row["price"])
            price_future = float(rows[i + HORIZON]["price"])
            entry = price_now * (1 + SLIPPAGE)
            exit_p = price_future * (1 - SLIPPAGE)
            gross_pct = (exit_p - entry) / entry * 100
            net_pct = gross_pct - COMMISSION * 2 * 100
            count += 1
            total_pct += net_pct
            if net_pct > 0:
                wins += 1
            else:
                losses += 1
        except:
            continue
    if count > 0:
        return {"count": count, "wr": wins / count * 100, "avg": total_pct / count}
    return None

def main():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    
    total = len(rows)
    split = int(total * 0.7)
    train = rows[:split]
    test = rows[split:]
    
    combos = [
        ("OI > 0.5% + delta < 0", lambda r: float(r.get("oi_change_5", 0)) > 0.5 and float(r.get("delta", 0)) < 0),
        ("OI > 0.5% + RSI < 30", lambda r: float(r.get("oi_change_5", 0)) > 0.5 and float(r.get("rsi", 50)) < 30),
        ("OI > 0.5% + vol > 3000", lambda r: float(r.get("oi_change_5", 0)) > 0.5 and float(r.get("vol24h", 0)) > 3000),
        ("delta < 0 + vol > 3000", lambda r: float(r.get("delta", 0)) < 0 and float(r.get("vol24h", 0)) > 3000),
        ("RSI < 30 + vol > 3000", lambda r: float(r.get("rsi", 50)) < 30 and float(r.get("vol24h", 0)) > 3000),
        ("OI > 0.5% + delta < 0 + vol > 3000", lambda r: float(r.get("oi_change_5", 0)) > 0.5 and float(r.get("delta", 0)) < 0 and float(r.get("vol24h", 0)) > 3000),
    ]
    
    print(f"Train: {len(train)} | Test: {len(test)}\n")
    print(f"{'═' * 60}")
    print("📐 A+ ЛОГИКА БЕЗ ФАЗ")
    print(f"{'═' * 60}")
    
    for name, fn in combos:
        tr = backtest(train, fn)
        te = backtest(test, fn)
        
        tr_str = f"{tr['count']} | {tr['wr']:.1f}% | {tr['avg']:+.3f}%" if tr else "нет данных"
        te_str = f"{te['count']} | {te['wr']:.1f}% | {te['avg']:+.3f}%" if te else "нет данных"
        
        print(f"\n{name}")
        print(f"  Train: {tr_str}")
        print(f"  Test:  {te_str}")

if __name__ == "__main__":
    main()
