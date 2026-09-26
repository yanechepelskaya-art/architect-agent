import csv
from datetime import datetime
import math

def bollinger_width(prices, period=20, mult=2):
    """Ширина канала Боллинджера в %."""
    if len(prices) < period:
        return None
    window = prices[-period:]
    ma = sum(window) / period
    var = sum((p - ma) ** 2 for p in window) / period
    sd = math.sqrt(var)
    if ma == 0:
        return None
    width = (2 * mult * sd) / ma * 100
    return width

def adx(prices, period=14):
    """Упрощённый ADX по ценам."""
    if len(prices) < period + 1:
        return None
    diffs = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    recent = diffs[-period:]
    up = sum(d for d in recent if d > 0)
    down = sum(-d for d in recent if d < 0)
    total = up + down
    if total == 0:
        return 0
    dx = abs(up - down) / total * 100
    return dx


RANGE_THRESHOLD = 1.5  # % — цена не выходит за этот диапазон
MIN_HOURS = 2          # минимум часов для боковика

def load_prices():
    prices = []
    # btc_data.csv — 13-22 сентября
    try:
        with open("btc_data.csv", "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                try:
                    t = datetime.strptime(r["time"], "%Y-%m-%d %H:%M:%S")
                    p = float(r["price"])
                    prices.append((t, p))
                except Exception:
                    continue
    except FileNotFoundError:
        pass
    # btc_data_v3.csv — 25-26 сентября
    try:
        with open("btc_data_v3.csv", "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                try:
                    t = datetime.strptime(r["time"], "%Y-%m-%d %H:%M:%S")
                    p = float(r["price"])
                    prices.append((t, p))
                except Exception:
                    continue
    except FileNotFoundError:
        pass
    prices.sort(key=lambda x: x[0])
    return prices

def find_sideways(prices):
    sideways = []
    i = 0
    while i < len(prices):
        start_t, start_p = prices[i]
        hi = start_p
        lo = start_p
        j = i
        while j < len(prices):
            t, p = prices[j]
            new_hi = max(hi, p)
            new_lo = min(lo, p)
            rng = (new_hi - new_lo) / new_lo * 100
            if rng > RANGE_THRESHOLD:
                break
            hi, lo = new_hi, new_lo
            j += 1
        duration_h = (prices[j-1][0] - prices[i][0]).total_seconds() / 3600 if j > i else 0
        if duration_h >= MIN_HOURS:
            sideways.append((prices[i][0], prices[j-1][0], duration_h, lo, hi))
            i = j
        else:
            i += 1
    return sideways

def main():
    prices = load_prices()
    if not prices:
        print("Нет данных.")
        return
    print(f"Всего строк: {len(prices)}")
    print(f"Период: {prices[0][0]} — {prices[-1][0]}")
    print("")

    sideways = find_sideways(prices)
    print(f"Найдено боковиков: {len(sideways)}")
    print("")

    if not sideways:
        print("Боковиков не найдено.")
        return

    durations = [s[2] for s in sideways]
    avg_h = sum(durations) / len(durations)
    median_h = sorted(durations)[len(durations)//2]
    max_h = max(durations)
    min_h = min(durations)

    print("=== СТАТИСТИКА ===")
    print(f"Средний боковик: {avg_h:.1f} ч ({avg_h/24:.2f} дн)")
    print(f"Медиана: {median_h:.1f} ч")
    print(f"Минимум: {min_h:.1f} ч")
    print(f"Максимум: {max_h:.1f} ч ({max_h/24:.2f} дн)")
    print("")

    print("=== ПОСЛЕДНИЕ 5 БОКОВИКОВ ===")
    for s in sideways[-5:]:
        print(f"{s[0]} → {s[1]} | {s[2]:.1f} ч | ${s[3]:.0f}–${s[4]:.0f}")

    # Текущий боковик
    now = prices[-1][0]
    # Найти последний непрерывный отрезок от now назад
    i = len(prices) - 1
    hi = prices[i][1]
    lo = prices[i][1]
    while i > 0:
        t, p = prices[i-1]
        new_hi = max(hi, p)
        new_lo = min(lo, p)
        rng = (new_hi - new_lo) / new_lo * 100
        if rng > RANGE_THRESHOLD:
            break
        hi, lo = new_hi, new_lo
        i -= 1
    current_h = (prices[-1][0] - prices[i][0]).total_seconds() / 3600
    print("")
    print("=== ТЕКУЩИЙ ===")
    print(f"С {prices[i][0]} по {prices[-1][0]}")
    print(f"Длительность: {current_h:.1f} ч ({current_h/24:.2f} дн)")
    print(f"Диапазон: ${lo:.0f}–${hi:.0f}")
    print("")
    if current_h > max_h:
        print("Статус: ДОЛЬШЕ МАКСИМУМА. Что-то новое.")
    elif current_h > avg_h:
        print(f"Статус: ЗА СРЕДНИМ. Средний {avg_h:.1f} ч, текущий {current_h:.1f} ч.")
    else:
        print(f"Статус: В НОРМЕ. Средний {avg_h:.1f} ч, текущий {current_h:.1f} ч.")

if __name__ == "__main__":
    main()

    prices_only = [p for (_, p) in load_prices()]
    bw = bollinger_width(prices_only, 20)
    adx_val = adx(prices_only, 14)
    print("")
    print("=== МЕТРИКИ (текущие) ===")
    if bw is not None:
        print(f"Bollinger Width: {bw:.2f}%")
    else:
        print("Bollinger Width: недостаточно данных")
    if adx_val is not None:
        print(f"ADX: {adx_val:.1f}")
    else:
        print("ADX: недостаточно данных")
    print("")
    print("Интерпретация:")
    if bw is not None and bw < 1.0:
        print("- Bollinger: узкий → сжатие")
    elif bw is not None:
        print("- Bollinger: широкий → движение")
    if adx_val is not None and adx_val < 20:
        print("- ADX < 20 → нет тренда, боковик")
    elif adx_val is not None:
        print("- ADX > 20 → тренд формируется")

