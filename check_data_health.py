import csv
from pathlib import Path

DATA_PATH = Path.home() / "Desktop" / "btc_data.csv"

def check():
    if not DATA_PATH.exists():
        print("❌ btc_data.csv не найден")
        return
    
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"Загружено {len(rows)} строк\n")
    
    # Проверка на NaN
    nan_count = 0
    for i, row in enumerate(rows):
        for key, val in row.items():
            if val is None or val == "" or val == "nan" or val == "None":
                nan_count += 1
                if nan_count <= 5:
                    print(f"⚠️ NaN: строка {i+2}, поле {key}")
                break
    
    print(f"\nВсего строк с NaN: {nan_count}")
    
    # Проверка на дубли
    seen = set()
    dup_count = 0
    for row in rows:
        t = row.get("time", "")
        if t in seen:
            dup_count += 1
            if dup_count <= 5:
                print(f"⚠️ Дубль: {t}")
        seen.add(t)
    
    print(f"Всего дублей: {dup_count}")
    
    # Проверка на гэпы во времени
    from datetime import datetime
    gap_count = 0
    prev_time = None
    for row in rows:
        try:
            t = datetime.fromisoformat(row["time"])
            if prev_time:
                diff = (t - prev_time).total_seconds() / 60
                if diff > 2:
                    gap_count += 1
                    if gap_count <= 5:
                        print(f"⚠️ Гэп: {prev_time} → {t} ({diff:.0f} мин)")
            prev_time = t
        except:
            continue
    
    print(f"Всего гэпов: {gap_count}")
    
    # Проверка цен на аномалии
    prices = []
    for row in rows:
        try:
            prices.append(float(row["price"]))
        except:
            pass
    
    if prices:
        min_p = min(prices)
        max_p = max(prices)
        avg_p = sum(prices) / len(prices)
        print(f"\nЦены:")
        print(f"  Мин: ${min_p:,.0f}")
        print(f"  Макс: ${max_p:,.0f}")
        print(f"  Средняя: ${avg_p:,.0f}")
        
        # Аномалии: цена < 50% или > 150% от средней
        anomalies = [p for p in prices if p < avg_p * 0.5 or p > avg_p * 1.5]
        print(f"  Аномалии: {len(anomalies)}")
    
    print("\n✅ Проверка завершена")

if __name__ == "__main__":
    check()
