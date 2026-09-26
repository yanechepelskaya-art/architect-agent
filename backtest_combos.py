import csv
from pathlib import Path

DATA_PATH = Path.home() / "Desktop" / "training_data.csv"

COMMISSION = 0.001   # 0.1% за сделку
SLIPPAGE = 0.0005    # 0.05% на вход/выход

def backtest_combo(rows, phase_filter, extra_filter, name, horizon=30):
    wins = 0
    losses = 0
    total_pct = 0.0
    count = 0
    
    for i, row in enumerate(rows):
        if row.get("phase") != phase_filter:
            continue
        if i + horizon >= len(rows):
            continue
        try:
            if not extra_filter(row):
                continue
            
            price_now = float(row["price"])
            price_future = float(rows[i + horizon]["price"])
            
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
        print(f"{name}: {count} сигналов | Винрейт: {winrate:.1f}% | Средний: {avg:+.3f}%")
    else:
        print(f"{name}: нет данных")

def main():
    if not DATA_PATH.exists():
        print("❌ training_data.csv не найден")
        return
    
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"Загружено {len(rows)} строк")
    print(f"Издержки: комиссия {COMMISSION*100}%, проскальзывание {SLIPPAGE*100}%\n")
    
    print("📊 КОМБИНАЦИИ (с издержками, горизонт 30 минут):\n")
    
    backtest_combo(rows, "impulse",
        lambda r: float(r.get("oi_change_5", 0)) > 0,
        "Impulse + oi_change_5 > 0")
    
    backtest_combo(rows, "impulse",
        lambda r: float(r.get("rsi", 50)) < 40,
        "Impulse + RSI < 40")
    
    backtest_combo(rows, "impulse",
        lambda r: float(r.get("delta", 0)) < 0,
        "Impulse + delta < 0")
    
    backtest_combo(rows, "impulse",
        lambda r: float(r.get("oi_change_5", 0)) > 0 and float(r.get("rsi", 50)) < 40,
        "Impulse + oi_change > 0 + RSI < 40")
    
    backtest_combo(rows, "impulse",
        lambda r: float(r.get("oi_change_5", 0)) > 0 and float(r.get("delta", 0)) < 0,
        "Impulse + oi_change > 0 + delta < 0")
    
    backtest_combo(rows, "emanation",
        lambda r: float(r.get("oi_change_5", 0)) > 0,
        "Emanation + oi_change_5 > 0")
    
    backtest_combo(rows, "emanation",
        lambda r: float(r.get("rsi", 50)) < 40,
        "Emanation + RSI < 40")

if __name__ == "__main__":
    main()
