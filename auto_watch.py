import os
os.environ["HTTPS_PROXY"] = "socks5://127.0.0.1:10808"
os.environ["HTTP_PROXY"] = "socks5://127.0.0.1:10808"
import time
import requests
from datetime import datetime

TOKEN = "8900618226:AAHvlytv83BqdhCuapsvbNDLAkPSyW1ZWyU"
MODE = "virtual"  # "virtual" или "real"
CHAT_ID = "870512243"

ZONE = 76986
STOP = 76213
TARGET1 = 78534
TARGET2 = 79694

CHECK_INTERVAL = 300
ZONE_TOLERANCE = 150
MIN_VOLUME = 2500

# Макро-события (дата и время в формате YYYY-MM-DD HH:MM)
MACRO_EVENTS = [
    # Актуальные события. Обновляй по мере появления.
    # Формат: {"date": "YYYY-MM-DD HH:MM", "name": "Название"}
]
last_macro_notified = {}

last_notified = None
last_phase = None
last_direction = None
last_move_notified = None
last_funding_notified = None
trade_price = None
trade_time = None

def send_tg(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def get_data():
    try:
        r = requests.get(
            "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT",
            timeout=10
        )
        d = r.json()["data"][0]
        return {
            "price": float(d["last"]),
            "vol24h": float(d["vol24h"]),
        }
    except Exception:
        return None

def get_recent_volume():
    try:
        r = requests.get(
            "https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=5m&limit=1",
            timeout=10
        )
        d = r.json()["data"][0]
        return float(d[5])
    except Exception:
        return 0

def check_aplus(price, vol_5m):
    """Проверка A+ сигнала"""
    try:
        # Получаем свечи 5м для дельты
        r = requests.get(
            "https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=5m&limit=6",
            timeout=10
        )
        data = r.json()["data"]

        buy_vol = 0
        sell_vol = 0
        for c in data:
            o = float(c[1]); cl = float(c[4]); v = float(c[5])
            if cl >= o:
                buy_vol += v
            else:
                sell_vol += v
        total = buy_vol + sell_vol
        buy_pct = buy_vol / total * 100 if total else 0

        # Получаем 24ч данные
        r2 = requests.get(
            "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT",
            timeout=10
        )
        d2 = r2.json()["data"][0]
        open24 = float(d2["open24h"])
        change_pct = (price - open24) / open24 * 100

        # Проверки
        reasons = []
        if vol_5m >= 2500:
            reasons.append(f"✅ Объём: {vol_5m:,.0f} BTC")
        if buy_pct >= 55:
            reasons.append(f"✅ Дельта: {buy_pct:.1f}% покупатели")
        if change_pct >= 1:
            reasons.append(f"✅ Рост: +{change_pct:.2f}%")

        # A+ = все три условия
        if vol_5m >= 2500 and buy_pct >= 55 and change_pct >= 1:
            return True, reasons
        return False, reasons
    except Exception as e:
        return False, [f"Ошибка: {e}"]

def execute_trade(price, vol_5m):
    """Виртуальная или реальная сделка"""
    import datetime as _dt
    ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if MODE == "virtual":
        with open("virtual_trades.log", "a") as f:
            f.write(f"{ts} | VIRTUAL BUY | price={price} | vol={vol_5m}\n")
        send_tg(
            f"🧪 <b>ВИРТУАЛЬНАЯ СДЕЛКА</b>\n\n"
            f"₿ BTC: ${price:,.0f}\n"
            f"📊 Объём: {vol_5m:,.0f} BTC\n"
            f"⏰ {ts}\n\n"
            f"📐 Режим: виртуальный"
        )
    else:
        send_tg(
            f"💰 <b>РЕАЛЬНАЯ СДЕЛКА</b>\n\n"
            f"⚠️ API не подключён.\n"
            f"Нужны ключи OKX."
        )

def detect_direction(price, chg):
    if chg > 1:
        return "Север"
    elif chg < -1:
        return "Юг"
    else:
        return "Восток"

def check_macro_events():
    """Проверяет приближение макро-событий"""
    from datetime import datetime as _dt
    now = _dt.now()
    for ev in MACRO_EVENTS:
        try:
            ev_time = _dt.strptime(ev["date"], "%Y-%m-%d %H:%M")
            delta_min = (ev_time - now).total_seconds() / 60
            if 55 <= delta_min <= 65:
                key = ev["name"]
                if not last_macro_notified.get(key):
                    send_tg(
                        f"📅 <b>СОБЫТИЕ ЧЕРЕЗ 1 ЧАС</b>\n\n"
                        f"🏛 <b>{ev['name']}</b>\n"
                        f"⏰ {ev['date']}\n\n"
                        f"⚠️ Без A+ не входить.\n"
                        f"⚠️ Плечо ≤ 10x."
                    )
                    last_macro_notified[key] = True
        except Exception:
            pass

def detect_phase(price, vol_5m):
    try:
        r = requests.get(
            "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT",
            timeout=10
        )
        d = r.json()["data"][0]
        chg = (float(d["last"]) - float(d["open24h"])) / float(d["open24h"]) * 100
    except Exception:
        chg = 0

    if abs(chg) < 0.3:
        return "⚪ Сжатие"
    elif 0.3 <= abs(chg) < 1.5:
        return "🟡 Импульс"
    elif abs(chg) >= 1.5 and chg > 0:
        return "🟢 Эманация"
    elif abs(chg) >= 1.5 and chg < 0:
        return "🔴 Вынос"
    return "⚪ Сжатие"

def check_verdict():
    # Автообновление Сенсора
    try:
        import agent_light
        df = agent_light.get_recent_candles(symbol="BTC-USDT", timeframe="5m", limit=100)
        agent_light.calculate_pressure_score(df, period=24)
    except Exception as e:
        print("SENSOR_ERR", e)

    # Автообновление результатов сигналов
    try:
        import update_results
        update_results.update_results()
    except Exception as e:
        print("RESULTS_ERR", e)

    """Проверяет signal_log.csv и отправляет уведомление, если все блокеры сняты."""
    try:
        import csv, datetime
        from pathlib import Path as P
        log_path = P.home() / "Desktop" / "signal_log.csv"
        if not log_path.exists():
            return

        latest = {}
        with open(log_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) >= 5:
                    latest[row[1]] = {"time": row[0], "price": row[2], "readiness": row[3], "layers": row[4]}

        def fresh(rec):
            try:
                t = datetime.datetime.fromisoformat(rec["time"])
                return (datetime.datetime.now() - t).total_seconds() < 900
            except:
                return False

        aplus = latest.get("A+")
        impulse = latest.get("Импульс")
        shadow = latest.get("Тень")

        blockers = []
        if aplus and fresh(aplus):
            try:
                score = int(aplus["layers"]) if aplus["layers"] else 0
                if score < 6:
                    blockers.append(f"A+: {score}/9")
            except:
                blockers.append("A+: нет данных")
        else:
            blockers.append("A+: нет свежих данных")

        if impulse and fresh(impulse):
            try:
                rd = int(impulse["readiness"]) if impulse["readiness"] else 0
                if rd < 50:
                    blockers.append(f"Импульс: {rd}%")
            except:
                blockers.append("Импульс: нет данных")
        else:
            blockers.append("Импульс: нет свежих данных")

        if shadow and fresh(shadow):
            layers = shadow["layers"].split("|")
            if len(layers) >= 2 and layers[1] in ("сильная", "средняя"):
                blockers.append(f"Тень: {layers[1]}")
        else:
            blockers.append("Тень: нет свежих данных")

        global last_verdict_notified
        if not blockers:
            if last_verdict_notified != "ok":
                price_now = aplus["price"] if aplus else (impulse["price"] if impulse else "—")
                send_tg(
                    f"🧿 <b>ВЕРДИКТ: ВОЗМОЖЕН ВХОД</b>\n\n"
                    f"₿ BTC: ${price_now}\n\n"
                    f"✅ Все блокеры сняты.\n"
                    f"🎯 Проверь зону и A+.\n\n"
                    f"📐 <i>Чертёж: вердикт — карта решений, не команда.</i>"
                )
                last_verdict_notified = "ok"
        else:
            last_verdict_notified = None
    except Exception as e:
        print("VERDICT_ERR", e)


def check():

    global last_notified
    data = get_data()
    if not data:
        return

    price = data["price"]
    vol_5m = get_recent_volume()
    now = datetime.now().strftime("%H:%M")

    near_zone = abs(price - ZONE) <= ZONE_TOLERANCE
    strong_vol = vol_5m >= MIN_VOLUME

    # Проверка A+
    aplus, reasons = check_aplus(price, vol_5m)

    # Автовход: A+ + зона + объём
    # ── Уведомление об A+ ──
    # ── Проверка смены фазы ──
    # ── Проверка смены направления ──
    global last_direction
    try:
        r_dir = requests.get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT", timeout=10)
        dd = r_dir.json()["data"][0]
        chg_dir = (float(dd["last"]) - float(dd["open24h"])) / float(dd["open24h"]) * 100
        current_dir = detect_direction(price, chg_dir)
        if last_direction is None:
            last_direction = current_dir
        elif current_dir != last_direction:
            send_tg(
                f"🔄 <b>СМЕНА НАПРАВЛЕНИЯ</b>\n\n"
                f"₿ BTC: ${price:,.0f}\n"
                f"Было: {last_direction}\n"
                f"Стало: <b>{current_dir}</b>\n\n"
                f"📐 Смена возможна."
            )
            last_direction = current_dir
    except Exception:
        pass

    # ── Проверка макро-событий ──
    check_macro_events()


    # ── Проверка сильного движения ──
    global last_move_notified
    try:
        r_mv = requests.get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=2", timeout=10)
        mv_data = r_mv.json()["data"][::-1]
        if len(mv_data) >= 2:
            open_15 = float(mv_data[0][1])
            close_15 = float(mv_data[-1][4])
            move_pct = (close_15 - open_15) / open_15 * 100
            if abs(move_pct) >= 2 and last_move_notified != "yes":
                direction = "вверх" if move_pct > 0 else "вниз"
                send_tg(
                    f"⚡ <b>СИЛЬНОЕ ДВИЖЕНИЕ</b>\n\n"
                    f"₿ BTC: ${price:,.0f}\n"
                    f"Δ: {move_pct:+.2f}% за 15 мин\n"
                    f"Направление: {direction}\n\n"
                    f"📐 Возможен вынос."
                )
                last_move_notified = "yes"
            elif abs(move_pct) < 1:
                last_move_notified = None
    except Exception:
        pass


    # ── Проверка funding-перекоса ──
    global last_funding_notified
    try:
        r_fr = requests.get("https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP", timeout=10)
        fr_data = r_fr.json()["data"][0]
        fr_val = float(fr_data["fundingRate"]) * 100
        if abs(fr_val) >= 0.05 and last_funding_notified != "yes":
            if fr_val > 0:
                crowd = "в лонгах"
                risk = "вынос вниз"
            else:
                crowd = "в шортах"
                risk = "вынос вверх"
            send_tg(
                f"⚡ <b>FUNDING-ПЕРЕКОС</b>\n\n"
                f"₿ BTC: ${price:,.0f}\n"
                f"Funding: {fr_val:+.4f}%\n"
                f"Толпа: {crowd}\n"
                f"Риск: {risk}\n\n"
                f"📐 Топливо для выноса."
            )
            last_funding_notified = "yes"
        elif abs(fr_val) < 0.03:
            last_funding_notified = None
    except Exception:
        pass


    global last_phase
    current_phase = detect_phase(price, vol_5m)
    if last_phase is None:
        last_phase = current_phase
    elif current_phase != last_phase:
        # Уведомление ТОЛЬКО при смене на Импульс
        if "Импульс" in current_phase or "импульс" in current_phase:
            # Проверка импульса: пробой + объём
            pulse_ok = False
            pulse_note = "⚠️ Импульс не подтверждён: пробоя нет, объём слабый"
            try:
                r_imp = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d_imp = r_imp.json()["data"][0]
                vol_now = float(d_imp.get("vol24h", 0))
                if vol_now > 5000:
                    pulse_ok = True
                    pulse_note = "✅ Импульс подтверждён: объём растёт"
                else:
                    pulse_note = f"⚠️ Импульс не подтверждён: объём {vol_now:,.0f} < 5000"
            except Exception:
                pass

            # Отправляем ТОЛЬКО если импульс подтверждён
            if pulse_ok:
                send_tg(
                    f"🔄 <b>СМЕНА ФАЗЫ: ИМПУЛЬС</b>\n\n"
                    f"₿ BTC: ${price:,.0f}\n\n"
                    f"Было: {last_phase}\n"
                    f"Стало: <b>{current_phase}</b>\n\n"
                    f"{pulse_note}\n\n"
                    f"📐 Вход — только по сигналу A+."
                )
        last_phase = current_phase
        last_phase = current_phase

    if aplus and last_notified != "aplus" and last_notified != "trade":
        send_tg(
            f"🎯 <b>A+ ОТКРЫТ</b>\n\n"
            f"₿ BTC: ${price:,.0f}\n"
            f"📊 Объём: {vol_5m:,.0f} BTC\n\n"
            f"🎯 Зона: ${ZONE:,}\n"
            f"🛑 Стоп: ${STOP:,}\n"
            f"🎯 Цель 1: ${TARGET1:,}\n"
            f"🎯 Цель 2: ${TARGET2:,}\n\n"
            f"📐 Вход — только от зоны."
        )
        last_notified = "aplus"


    if aplus and near_zone and strong_vol and last_notified != "trade":
        global trade_price, trade_time
        execute_trade(price, vol_5m)
        trade_price = price
        trade_time = time.time()
        send_tg(
            f"🎯 <b>A+ ОТКРЫТ + ЗОНА</b>\n\n"
            f"₿ BTC: ${price:,.0f}\n"
            f"🎯 Зона: ${ZONE:,}\n"
            f"📊 Объём 5м: {vol_5m:,.0f} BTC\n\n" +
            "\n".join(reasons) +
            f"\n⏰ {now}"
        )
        last_notified = "trade"

    if near_zone and strong_vol:
        if last_notified != "signal":
            send_tg(
                f"⚡ <b>СИГНАЛ: ЦЕНА У ЗОНЫ + ОБЪЁМ</b>\n\n"
                f"₿ BTC: ${price:,.0f}\n"
                f"🎯 Зона: ${ZONE:,}\n"
                f"🛑 Стоп: ${STOP:,}\n"
                f"🎯 Цель 1: ${TARGET1:,}\n"
                f"🎯 Цель 2: ${TARGET2:,}\n\n"
                f"📊 Объём 5м: {vol_5m:,.0f} BTC ✅\n"
                f"⏰ {now}\n\n"
                f"📐 Проверь A+ и импульс."
            )
            last_notified = "signal"
    elif near_zone:
        if last_notified != "zone":
            send_tg(
                f"⚡ <b>ЦЕНА У ЗОНЫ</b>\n\n"
                f"₿ BTC: ${price:,.0f}\n"
                f"📊 Объём 5м: {vol_5m:,.0f} BTC (мало)\n"
                f"⏰ {now}\n\n"
                f"📐 Ждём объём."
            )
            last_notified = "zone"
    else:
        if last_notified in ("zone", "signal"):
            last_notified = None

    # Проверка безубытка
    # ── Проверка TP ──
    if trade_price is not None and last_notified == "trade":
        if price >= TARGET1:
            send_tg(
                f"🎯 <b>ЦЕЛЬ 1 ДОСТИГНУТА</b>\n\n"
                f"₿ BTC: ${price:,.0f}\n"
                f"🎯 Цель 1: ${TARGET1:,}\n\n"
                f"💰 Фиксируй 50%.\n"
                f"🛡 Стоп → безубыток.\n\n"
                f"📐 Остаток — к цели ${TARGET2:,}."
            )
            last_notified = "tp1"

    if trade_price is not None and last_notified == "tp1":
        if price >= TARGET2:
            send_tg(
                f"🎯 <b>ЦЕЛЬ 2 ДОСТИГНУТА</b>\n\n"
                f"₿ BTC: ${price:,.0f}\n"
                f"🎯 Цель 2: ${TARGET2:,}\n\n"
                f"💰 Фиксируй всё.\n"
                f"📐 Сделка закрыта."
            )
            last_notified = "tp2"

    # ── Проверка стопа ──
    if trade_price is not None and last_notified in ("trade", "signal"):
        if price <= STOP:
            send_tg(
                f"🛑 <b>СТОП СРАБОТАЛ</b>\n\n"
                f"₿ BTC: ${price:,.0f}\n"
                f"🛑 Стоп: ${STOP:,}\n\n"
                f"📐 Выход по системе.\n"
                f"💰 Сохранил капитал."
            )
            last_notified = "stopped"

    # ── Проверка безубытка ──
    if trade_price is not None and last_notified == "trade":
        if price >= trade_price * 1.005:
            with open("virtual_trades.log", "a") as f:
                f.write(f"VIRTUAL BREAKEVEN | entry={trade_price} | now={price}\n")
            send_tg(
                f"🛡 <b>ВИРТУАЛЬНЫЙ БЕЗУБЫТОК</b>\n\n"
                f"Вход: ${trade_price:,.0f}\n"
                f"Текущая: ${price:,.0f}\n"
                f"📐 Риск снят."
            )
            last_notified = "breakeven"

if __name__ == "__main__":
    send_tg("🔔 <b>Автономный режим V2 запущен</b>\n\nСлежу за зоной $" + f"{ZONE:,}" + " + объёмом")
    while True:
        check()
        check_verdict()
        time.sleep(CHECK_INTERVAL)
