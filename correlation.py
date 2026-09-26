import csv
from pathlib import Path

DATA_PATH = Path.home() / "Desktop" / "training_data.csv"

def pearson(x, y):
    n = len(x)
    if n == 0:
        return 0
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    num = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    den_x = sum((x[i] - mean_x) ** 2 for i in range(n)) ** 0.5
    den_y = sum((y[i] - mean_y) ** 2 for i in range(n)) ** 0.5
    if den_x == 0 or den_y == 0:
        return 0
    return num / (den_x * den_y)

def main():
    if not DATA_PATH.exists():
        print("❌ training_data.csv не найден")
        return
    
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    
    print(f"Загружено {len(rows)} строк\n")
    
    # Фичи
    features = ["delta", "rsi", "oi_change_5", "vol24h", "atr", "price_change_5"]
    
    # Собираем данные
    data = {f: [] for f in features}
    for row in rows:
        try:
            for f in features:
                data[f].append(float(row.get(f, 0)))
        except:
            continue
    
    print("📊 МАТРИЦА КОРРЕЛЯЦИЙ:\n")
    
    # Заголовок
    header = " " * 15
    for f in features:
        header += f"{f[:8]:>10}"
    print(header)
    
    # Строки
    for f1 in features:
        line = f"{f1[:12]:<14}"
        for f2 in features:
            corr = pearson(data[f1], data[f2])
            line += f"{corr:>10.2f}"
        print(line)
    
    print("\n📐 Чертёж: корреляция > 0.7 — дубли. Убирать.")

if __name__ == "__main__":
    main()
