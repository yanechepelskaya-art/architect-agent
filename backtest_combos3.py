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
    print("📊 НОВЫЕ КОМБИНАЦИИ:\n")
    
    # OI + Volume
    backtest(rows, lambda r: float(r.get("oi_change_5", 0)) > 0.5 and float(r.get("vol24h", 0)) > 5000,
        "OI > 0.5% + Volume > 5000")
    
    backtest(rows, lambda r: float(r.get("oi_change_5", 0)) > 0.5 and float(r.get("vol24h", 0)) < 3000,
        "OI > 0.5% + Volume < 3000")
    
    # OI + ATR
    backtest(rows, lambda r: float(r.get("oi_change_5", 0)) > 0.5 and float(r.get("atr", 0)) > 50,
        "OI > 0.5% + ATR > 50")
    
    # OI + price change
    backtest(rows, lambda r: float(r.get("oi_change_5", 0)) > 0.5 and float(r.get("price_change_5", 0)) < -0.2,
        "OI > 0.5% + price_change < -0.2%")
    
    # Flush + Volume
    backtest(rows, lambda r: r.get("phase") == "flush" and float(r.get("vol24h", 0)) > 5000,
        "Flush + Volume > 5000")
    
    # Flush + ATR
    backtest(rows, lambda r: r.get("phase") == "flush" and float(r.get("atr", 0)) > 50,
        "Flush + ATR > 50")
    
    # Emanation + Volume
    backtest(rows, lambda r: r.get("phase") == "emanation" and float(r.get("vol24h", 0)) > 5000,
        "Emanation + Volume > 5000")
    
    # Emanation + ATR
    backtest(rows, lambda r: r.get("phase") == "emanation" and float(r.get("atr", 0)) > 50,
        "Emanation + ATR > 50")
    
    # OI + emanation + RSI
    backtest(rows, lambda r: float(r.get("oi_change_5", 0)) > 0.5 and r.get("phase") == "emanation" and float(r.get("rsi", 50)) < 50,
        "OI > 0.5% + emanation + RSI < 50")
    
    # OI + flush + RSI
    backtest(rows, lambda r: float(r.get("oi_change_5", 0)) > 0.5 and r.get("phase") == "flush" and float(r.get("rsi", 50)) < 50,
        "OI > 0.5% + flush + RSI < 50")

if __name__ == "__main__":
    main()
