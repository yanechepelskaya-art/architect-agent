import csv
from pathlib import Path

DATA_PATH = Path.home() / "Desktop" / "training_data.csv"

COMMISSION = 0.001
SLIPPAGE = 0.0005

def backtest(rows, filter_fn, name, horizon=30):
    wins = 0
    losses = 0
    total_pct = 0.0
    count = 0
    
    for i, row in enumerate(rows):
        if i + horizon >= len(rows):
            continue
        try:
            if not filter_fn(row):
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
        print(f"{name}: {count} | Винрейт: {winrate:.1f}% | Средний: {avg:+.3f}%")
    else:
        print(f"{name}: нет данных")

def main():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    
    print(f"Загружено {len(rows)} строк\n")
    print("📊 КОМБИНАЦИИ СЛОЁВ:\n")
    
    # OI + RSI
    backtest(rows, lambda r: float(r.get("oi_change_5", 0)) > 0.5 and float(r.get("rsi", 50)) < 30,
        "OI > 0.5% + RSI < 30")
    
    backtest(rows, lambda r: float(r.get("oi_change_5", 0)) > 0.5 and float(r.get("rsi", 50)) > 70,
        "OI > 0.5% + RSI > 70")
    
    # OI + delta
    backtest(rows, lambda r: float(r.get("oi_change_5", 0)) > 0.5 and float(r.get("delta", 0)) > 0,
        "OI > 0.5% + Delta > 0")
    
    backtest(rows, lambda r: float(r.get("oi_change_5", 0)) > 0.5 and float(r.get("delta", 0)) < 0,
        "OI > 0.5% + Delta < 0")
    
    # OI + phase
    backtest(rows, lambda r: float(r.get("oi_change_5", 0)) > 0.5 and r.get("phase") == "emanation",
        "OI > 0.5% + emanation")
    
    backtest(rows, lambda r: float(r.get("oi_change_5", 0)) > 0.5 and r.get("phase") == "flush",
        "OI > 0.5% + flush")
    
    # Price change + phase
    backtest(rows, lambda r: float(r.get("price_change_5", 0)) < -0.2 and r.get("phase") == "emanation",
        "Price change < -0.2% + emanation")
    
    # ATR + OI
    backtest(rows, lambda r: float(r.get("atr", 0)) > 50 and float(r.get("oi_change_5", 0)) > 0.5,
        "ATR > 50 + OI > 0.5%")
    
    # RSI + phase
    backtest(rows, lambda r: float(r.get("rsi", 50)) < 30 and r.get("phase") == "emanation",
        "RSI < 30 + emanation")
    
    backtest(rows, lambda r: float(r.get("rsi", 50)) < 30 and r.get("phase") == "flush",
        "RSI < 30 + flush")

if __name__ == "__main__":
    main()
