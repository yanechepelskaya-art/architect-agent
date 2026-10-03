# merge_history.py — объединение btc_history + delta из btc_data_v3
import csv

HISTORY = "btc_history.csv"
DATA = "btc_data_v3.csv"
OUTPUT = "btc_history_delta.csv"

def main():
    # 1. Загрузить data (delta по часам)
    print("Загрузка btc_data_v3.csv...")
    delta_by_hour = {}
    with open(DATA, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                hour = r["time"][:13]  # YYYY-MM-DD HH
                delta = float(r.get("delta", 0))
                if hour not in delta_by_hour:
                    delta_by_hour[hour] = []
                delta_by_hour[hour].append(delta)
            except Exception:
                continue

    # Суммировать delta по часам
    delta_sum = {h: sum(v) for h, v in delta_by_hour.items()}
    print(f"  Часов с delta: {len(delta_sum)}")

    # 2. Загрузить history и добавить delta
    print("Обработка btc_history.csv...")
    rows_out = []
    with open(HISTORY, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            hour = r["time"][:13]
            d = delta_sum.get(hour, 0)
            r["delta_sum"] = round(d, 4)
            rows_out.append(r)

    # 3. Записать
    if not rows_out:
        print("Пусто.")
        return

    fieldnames = list(rows_out[0].keys())
    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows_out)

    print(f"OK: {OUTPUT} — {len(rows_out)} строк")

    # Проверка
    with_delta = sum(1 for r in rows_out if r["delta_sum"] != 0)
    print(f"Строк с ненулевой delta: {with_delta}")

if __name__ == "__main__":
    main()
