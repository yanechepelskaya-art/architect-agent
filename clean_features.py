import csv
from pathlib import Path

DATA_PATH = Path.home() / "Desktop" / "training_data.csv"
OUT_PATH = Path.home() / "Desktop" / "training_data_clean.csv"

# Колонки для удаления
DROP = ["high24h", "low24h", "oi", "price_change_5"]

def main():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"Загружено {len(rows)} строк")
    print(f"Колонки было: {list(rows[0].keys())}")
    
    # Оставляем только нужные
    keep = [k for k in rows[0].keys() if k not in DROP]
    print(f"Колонки стало: {keep}\n")
    
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keep)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in keep})
    
    print(f"✅ Сохранено {len(rows)} строк → training_data_clean.csv")

if __name__ == "__main__":
    main()
