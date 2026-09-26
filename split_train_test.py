import csv
import random
from pathlib import Path
from collections import defaultdict

DATA_PATH = Path.home() / "Desktop" / "training_data.csv"
TRAIN_PATH = Path.home() / "Desktop" / "train_data.csv"
TEST_PATH = Path.home() / "Desktop" / "test_data.csv"

random.seed(42)

def main():
    if not DATA_PATH.exists():
        print("❌ training_data.csv не найден")
        return
    
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Группируем по фазам
    by_phase = defaultdict(list)
    for row in rows:
        by_phase[row.get("phase", "unknown")].append(row)
    
    train = []
    test = []
    
    # Стратифицированный split: 70/30 в каждой фазе
    for phase, items in by_phase.items():
        random.shuffle(items)
        split_idx = int(len(items) * 0.7)
        train.extend(items[:split_idx])
        test.extend(items[split_idx:])
    
    # Перемешиваем финальные наборы
    random.shuffle(train)
    random.shuffle(test)
    
    # Записываем
    with open(TRAIN_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(train)
    
    with open(TEST_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(test)
    
    print(f"Всего: {len(rows)}")
    print(f"Train: {len(train)} (70%)")
    print(f"Test: {len(test)} (30%)")
    print(f"\n✅ train_data.csv и test_data.csv созданы (стратифицированно)")

if __name__ == "__main__":
    main()
