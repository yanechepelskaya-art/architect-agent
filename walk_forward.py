import csv
from pathlib import Path

DATA_PATH = Path.home() / "Desktop" / "training_data_clean.csv"

COMMISSION = 0.001
SLIPPAGE = 0.0005
HORIZON = 30  # 30 строк = 30 минут

def backtest_segment(rows, name):
    """Прогоняет A+ (фазы) на сегменте и возвращает метрики."""
    results = {}
    for phase_name in ["impulse", "emanation", "compression", "flush"]:
        wins = 0
        losses = 0
        total_pct = 0.0
        count = 0
        for i, row in enumerate(rows):
            if row.get("phase") != phase_name:
                continue
            if i + HORIZON >= len(rows):
                continue
            try:
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
            winrate = wins / count * 100
            avg = total_pct / count
            results[phase_name] = {"count": count, "winrate": winrate, "avg": avg}
    
    print(f"\n📊 {name}")
    print(f"{'─' * 40}")
    for phase, r in results.items():
        print(f"  {phase}: {r['count']} сигналов | {r['winrate']:.1f}% | {r['avg']:+.3f}%")
    return results

def main():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    
    total = len(rows)
    split = int(total * 0.7)
    
    train = rows[:split]
    test = rows[split:]
    
    print(f"Всего строк: {total}")
    print(f"Train: {len(train)} ({split/total*100:.0f}%)")
    print(f"Test: {len(test)} ({(total-split)/total*100:.0f}%)")
    
    train_res = backtest_segment(train, "TRAIN (прошлое)")
    test_res = backtest_segment(test, "TEST (будущее)")
    
    print(f"\n{'═' * 40}")
    print("📐 СРАВНЕНИЕ TRAIN vs TEST")
    print(f"{'═' * 40}")
    for phase in ["impulse", "emanation", "compression", "flush"]:
        tr = train_res.get(phase)
        te = test_res.get(phase)
        if tr and te:
            delta = te["avg"] - tr["avg"]
            print(f"  {phase}: train {tr['avg']:+.3f}% → test {te['avg']:+.3f}% (Δ {delta:+.3f}%)")

if __name__ == "__main__":
    main()
