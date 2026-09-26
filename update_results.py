import csv
import requests
import datetime
from pathlib import Path

LOG_PATH = Path.home() / "Desktop" / "signal_log.csv"

def get_price():
    try:
        r = requests.get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT", timeout=10)
        return float(r.json()["data"][0]["last"])
    except:
        return None

def get_direction(button, layers):
    """Определяет направление сигнала по layers."""
    if not layers:
        return None
    layers_lower = layers.lower()
    
    # Тень: "вверх|сильная|75"
    if button == "Тень":
        if "вверх" in layers_lower:
            return "вверх"
        if "вниз" in layers_lower:
            return "вниз"
    
    # Компас: "Север (вверх)", "Юг (вниз)", "Восток (боковик)"
    if button == "Компас":
        if "север" in layers_lower or "вверх" in layers_lower:
            return "вверх"
        if "юг" in layers_lower or "вниз" in layers_lower:
            return "вниз"
        return "боковик"
    
    # Дельта: "buy|sell"
    if button == "Дельта":
        parts = layers.split("|")
        if len(parts) >= 2:
            try:
                buy = float(parts[0])
                sell = float(parts[1])
                if buy > sell:
                    return "вверх"
                elif sell > buy:
                    return "вниз"
            except:
                pass
    
    # HTF: "🟢 Тренд вверх" / "🔴 Тренд вниз"
    if button == "HTF":
        if "вверх" in layers_lower:
            return "вверх"
        if "вниз" in layers_lower:
            return "вниз"
    
    # След ММ: "🟢 покупатели|ММ поднимает вверх"
    if button == "След ММ":
        if "вверх" in layers_lower:
            return "вверх"
        if "вниз" in layers_lower:
            return "вниз"
    
    # A+ и Импульс — направление не сохраняется в layers
    return None

def update_results():
    if not LOG_PATH.exists():
        print("❌ signal_log.csv не найден")
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
        button_i = header.index("button")
        price_i = header.index("price")
        layers_i = header.index("layers")
        result_i = header.index("result_30m")
        result_price_i = header.index("result_price")
        correct_i = header.index("correct")
    except ValueError as e:
        print(f"❌ Ошибка структуры: {e}")
        return

    current_price = get_price()
    if not current_price:
        print("❌ Не удалось получить цену")
        return

    updated = 0
    recalculated = 0
    now = datetime.datetime.now()

    for row in data:
        if len(row) <= correct_i:
            continue
        
        button = row[button_i]
        layers = row[layers_i] if len(row) > layers_i else ""
        
        # Обновляем результат, если ещё нет
        if not row[result_i]:
            try:
                signal_time = datetime.datetime.fromisoformat(row[time_i])
                age_min = (now - signal_time).total_seconds() / 60
                if age_min >= 30:
                    signal_price = float(row[price_i])
                    change_pct = (current_price - signal_price) / signal_price * 100
                    row[result_i] = f"{change_pct:+.2f}%"
                    row[result_price_i] = f"{current_price:.2f}"
                    updated += 1
            except Exception:
                continue
        
        # Пересчитываем correct на основе направления
        if row[result_i]:
            try:
                pct = float(row[result_i].replace("%", ""))
                direction = get_direction(button, layers)
                
                if direction == "вверх":
                    row[correct_i] = "✅" if pct > 0 else "❌"
                elif direction == "вниз":
                    row[correct_i] = "✅" if pct < 0 else "❌"
                elif direction == "боковик":
                    row[correct_i] = "➖" if abs(pct) < 0.5 else ("❌" if abs(pct) >= 0.5 else "➖")
                else:
                    # Направление неизвестно (A+, Импульс)
                    row[correct_i] = "—"
                recalculated += 1
            except Exception:
                continue

    with open(LOG_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data)

    print(f"✅ Обновлено {updated} записей, пересчитано {recalculated}")

if __name__ == "__main__":
    update_results()
