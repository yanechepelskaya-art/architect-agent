import csv
import math
from pathlib import Path

DATA_PATH = Path.home() / "Desktop" / "training_data.csv"

def pearson(x, y):
    n = len(x)
    if n == 0:
        return 0
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    dx = math.sqrt(sum((x[i] - mx) ** 2 for i in range(n)))
    dy = math.sqrt(sum((y[i] - my) ** 2 for i in range(n)))
    if dx == 0 or dy == 0:
        return 0
    return num / (dx * dy)

def main():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    
    print(f"Загружено {len(rows)} строк\n")
    
    # Числовые колонки
    numeric_cols = ["price", "vol24h", "high24h", "low24h", "oi", "funding", "delta", "atr", "rsi", "hour", "price_change_5", "oi_change_5"]
    
    # Собираем данные
    data = {}
    for col in numeric_cols:
        vals = []
        for row in rows:
            try:
                v = float(row.get(col, 0))
                if not math.isnan(v):
                    vals.append(v)
            except:
                vals.append(0.0)
        data[col] = vals
    
    # Матрица корреляций
    print("📊 МАТРИЦА КОРРЕЛЯЦИЙ:\n")
    print(f"{'':>18}", end="")
    for col in numeric_cols:
        print(f"{col[:8]:>10}", end="")
    print()
    
    for col1 in numeric_cols:
        print(f"{col1[:18]:>18}", end="")
        for col2 in numeric_cols:
            r = pearson(data[col1], data[col2])
            print(f"{r:>10.2f}", end="")
        print()

if __name__ == "__main__":
    main()
