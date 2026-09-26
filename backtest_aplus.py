import csv
from pathlib import Path

DATA_PATH = Path.home() / "Desktop" / "test_data.csv"

# Издержки
COMMISSION = 0.001   # 0.1% за сделку (вход + выход = 0.2%)
SLIPPAGE = 0.0005    # 0.05% на вход и выход

def backtest():
    if not DATA_PATH.exists():
        print("❌ training_data.csv не найден")
        return
    
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"Загружено {len(rows)} строк")
    print(f"Издержки: комиссия {COMMISSION*100}%, проскальзывание {SLIPPAGE*100}%\n")
    
    horizon = 30  # строк
    
    results = {}
    for phase_name in ["impulse", "emanation", "compression", "flush"]:
        wins = 0
        losses = 0
        total_pct = 0.0
        count = 0
        
        for i, row in enumerate(rows):
            if row.get("phase") != phase_name:
                continue
            if i + horizon >= len(rows):
                continue
            try:
                price_now = float(row["price"])
                price_future = float(rows[i + horizon]["price"])
                
                # Проскальзывание: вход дороже, выход дешевле
                entry = price_now * (1 + SLIPPAGE)
                exit_p = price_future * (1 - SLIPPAGE)
                
                # Комиссия: 0.1% на вход + 0.1% на выход
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
            results[phase_name] = {
                "count": count,
                "winrate": winrate,
                "avg_pct": avg,
                "wins": wins,
                "losses": losses,
            }
    
    print("📊 РЕАЛИСТИЧНЫЙ БЭКТЕСТ (горизонт 30 минут):\n")
    for phase_name, r in results.items():
        print(f"Фаза: {phase_name}")
        print(f"  Сигналов: {r['count']}")
        print(f"  Винрейт: {r['winrate']:.1f}%")
        print(f"  Средний результат: {r['avg_pct']:+.3f}%")
        print(f"  Прибыльных: {r['wins']} | Убыточных: {r['losses']}")
        print()

if __name__ == "__main__":
    backtest()
