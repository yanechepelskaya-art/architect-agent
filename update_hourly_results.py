import csv
import requests
import datetime
from pathlib import Path

LOG_PATH = Path.home() / "Desktop" / "hourly_forecast_log.csv"

def get_price():
    try:
        r = requests.get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT", timeout=10)
        return float(r.json()["data"][0]["last"])
    except:
        return None

def update():
    if not LOG_PATH.exists():
        print("❌ hourly_forecast_log.csv не найден")
        return

    with open(LOG_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if len(rows) < 2:
        print("❌ Нет данных")
        return

    header = rows[0]
    data = rows[1:]

    try:
        time_i = header.index("time")
        fact_1h_i = header.index("fact_1h")
        fact_2h_i = header.index("fact_2h")
        fact_4h_i = header.index("fact_4h")
    except ValueError as e:
        print(f"❌ Ошибка структуры: {e}")
        return

    current_price = get_price()
    if not current_price:
        print("❌ Не удалось получить цену")
        return

    now = datetime.datetime.now()
    updated = 0

    for row in data:
        if len(row) <= fact_4h_i:
            continue
        try:
            t = datetime.datetime.fromisoformat(row[time_i])
            age_min = (now - t).total_seconds() / 60

            if age_min >= 60 and not row[fact_1h_i]:
                row[fact_1h_i] = f"{current_price:.2f}"
                updated += 1
            if age_min >= 120 and not row[fact_2h_i]:
                row[fact_2h_i] = f"{current_price:.2f}"
                updated += 1
            if age_min >= 240 and not row[fact_4h_i]:
                row[fact_4h_i] = f"{current_price:.2f}"
                updated += 1
        except:
            continue

    with open(LOG_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data)

    print(f"✅ Обновлено {updated} записей")

if __name__ == "__main__":
    update()
