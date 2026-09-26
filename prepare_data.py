import csv

def detect_phase(chg_15):
    """Определяет фазу по изменению цены за 15 минут."""
    if abs(chg_15) < 0.3:
        return "compression"
    elif chg_15 >= 0.8:
        return "emanation"
    elif chg_15 <= -0.8:
        return "flush"
    elif 0.3 <= abs(chg_15) < 0.8:
        return "impulse"
    return "flat"

# Загружаем данные
rows = []
with open("btc_data.csv", "r") as f:
    reader = csv.reader(f)
    header = next(reader)
    for row in reader:
        rows.append(row)

print(f"Загружено {len(rows)} строк")

# Размечаем
with open("btc_data_labeled.csv", "w", newline="") as f_out:
    writer = csv.writer(f_out)
    writer.writerow(header + ["phase"])

    count = 0
    for i, row in enumerate(rows):
        try:
            close = float(row[1])
            # Изменение за 15 минут (15 строк назад)
            if i >= 15:
                prev_close = float(rows[i-15][1])
                chg_15 = (close - prev_close) / prev_close * 100 if prev_close > 0 else 0
                phase = detect_phase(chg_15)
            else:
                phase = "flat"
            writer.writerow(row + [phase])
            count += 1
        except Exception:
            continue

print(f"✅ Размечено {count} строк → btc_data_labeled.csv")
