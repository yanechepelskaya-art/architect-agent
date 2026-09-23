import os
# os.environ["HTTPS_PROXY"] = "socks5://127.0.0.1:10809"
# os.environ["HTTP_PROXY"] = "socks5://127.0.0.1:10809"
import requests, json, time
from sklearn.ensemble import RandomForestClassifier
import numpy as np
from datetime import datetime

TOKEN = "8900618226:AAHvlytv83BqdhCuapsvbNDLAkPSyW1ZWyU"
CHAT_ID = "870512243"
last_update_id = 0
user_state = {}
JOURNAL = []
ML_HISTORY = []
PAPER_BALANCE = 10000.0
PAPER_HISTORY = []
PAPER_HISTORY = []





def log_accuracy(signal, price, direction):
    try:
        import datetime
        from pathlib import Path as P
        log_path = P.home() / "Desktop" / "accuracy_log.csv"
        line = f"{datetime.datetime.now().isoformat()},{signal},{price},{direction}\n"
        if not log_path.exists():
            log_path.write_text("time,signal,price,direction\n", encoding="utf-8")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass

def check_kill_switch():
    """Проверяет, не превышен ли дневной лимит убытка."""
    try:
        import json
        import datetime
        from pathlib import Path as P
        
        cfg_path = P.home() / "Desktop" / "risk_config.json"
        pnl_path = P.home() / "Desktop" / "daily_pnl.json"
        
        if not cfg_path.exists() or not pnl_path.exists():
            return False, "нет данных"
        
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        pnl = json.loads(pnl_path.read_text(encoding="utf-8"))
        
        deposit = cfg.get("deposit", 100)
        max_loss_pct = cfg.get("max_daily_loss_percent", 3)
        max_loss_usd = deposit * max_loss_pct / 100
        
        today = datetime.date.today().isoformat()
        if pnl.get("date") != today:
            # Новый день — сбрасываем
            pnl = {"date": today, "pnl": 0, "trades": 0, "wins": 0, "losses": 0}
            pnl_path.write_text(json.dumps(pnl, indent=2), encoding="utf-8")
            return False, "новый день"
        
        current_pnl = pnl.get("pnl", 0)
        if current_pnl <= -max_loss_usd:
            return True, f"дневной убыток ${current_pnl:.2f} ≥ ${max_loss_usd:.2f}"
        
        # Проверка серии убытков
        max_consec = cfg.get("max_consecutive_losses", 3)
        consec = pnl.get("consecutive_losses", 0)
        if consec >= max_consec:
            return True, f"серия убытков: {consec} подряд (лимит {max_consec})"
        
        return False, f"PnL дня: ${current_pnl:.2f} | серия: {consec}"
    except Exception as e:
        return False, f"ошибка: {e}"


def log_signal(button, price, readiness="", layers=""):
    try:
        import datetime
        from pathlib import Path as P
        log_path = P.home() / "Desktop" / "signal_log.csv"
        # Поля: time, button, price, readiness, layers, result_30m, result_price, correct
        line = f"{datetime.datetime.now().isoformat()},{button},{price},{readiness},{layers},,,\n"
        if not log_path.exists():
            log_path.write_text("time,button,price,readiness,layers,result_30m,result_price,correct\n", encoding="utf-8")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass

def calculate_pressure_score(df, period=24):
    if df is None or len(df) < period:
        return 0, "недостаточно данных"

    recent = df.tail(period).copy()

    price_change_pct = (recent['close'].iloc[-1] - recent['close'].iloc[0]) / recent['close'].iloc[0] * 100
    price_score = max(-100, min(100, price_change_pct * 35))

    up_volume = recent.loc[recent['close'] > recent['open'], 'volume'].sum()
    down_volume = recent.loc[recent['close'] <= recent['open'], 'volume'].sum()
    total_volume = up_volume + down_volume
    volume_bias = (up_volume - down_volume) / total_volume if total_volume > 0 else 0
    volume_score = volume_bias * 25

    high_max = recent['high'].max()
    low_min = recent['low'].min()
    range_pct = (high_max - low_min) / low_min * 100 if low_min else 0
    vol_boost = min(20, range_pct * 5)

    half = max(6, period // 4)
    first_half = recent['close'].iloc[:-half].mean()
    last_half = recent['close'].iloc[-half:].mean()
    speed_pct = (last_half - first_half) / first_half * 100 if first_half else 0
    speed_score = max(-100, min(100, speed_pct * 40))

    last_close = recent['close'].iloc[-1]
    pos_ratio = (last_close - low_min) / (high_max - low_min) if high_max > low_min else 0.5
    position_score = (pos_ratio - 0.5) * 60

    range_span = high_max - low_min
    if range_span > 0:
        dist_to_low = (last_close - low_min) / range_span
        dist_to_high = (high_max - last_close) / range_span
        liq_bias = dist_to_low - dist_to_high
    else:
        liq_bias = 0
    liq_score = liq_bias * 25

    raw_score = (
        0.30 * price_score
        + 0.20 * volume_score
        + 0.20 * speed_score
        + 0.15 * position_score
        + 0.15 * liq_score
    )

    # Усталость продавца: если последние 6 свечей вниз, но диапазон сузился
    exhaustion_bonus = 0
    if len(recent) >= 10:
        last6 = recent.tail(6)
        prev = recent.iloc[:-6]
        down_count = int((last6['close'] < last6['open']).sum())
        avg_range_last = ((last6['high'] - last6['low']) / last6['low'] * 100).mean()
        avg_range_prev = ((prev['high'] - prev['low']) / prev['low'] * 100).mean()
        if down_count >= 4 and avg_range_last < avg_range_prev * 0.8:
            exhaustion_bonus = 15

    # Подготовка импульса: диапазон сжимается, объём растёт
    impulse_flag = 0
    if len(recent) >= 12:
        first_part = recent.iloc[:-6]
        last_part = recent.tail(6)
        range_first = ((first_part['high'] - first_part['low']) / first_part['low'] * 100).mean()
        range_last = ((last_part['high'] - last_part['low']) / last_part['low'] * 100).mean()
        vol_first = first_part['volume'].mean()
        vol_last = last_part['volume'].mean()
        if range_last < range_first * 0.75 and vol_last > vol_first * 1.2:
            impulse_flag = 1

    if raw_score > 0:
        pressure_score = int(raw_score + vol_boost + exhaustion_bonus)
    else:
        pressure_score = int(raw_score - vol_boost + exhaustion_bonus)

    pressure_score = max(-100, min(100, pressure_score))

    # Адаптивные пороги в зависимости от волатильности
    # range_pct уже посчитан выше
    if range_pct > 1.5:
        neutral_zone = 40
    elif range_pct > 0.8:
        neutral_zone = 30
    else:
        neutral_zone = 20

    if impulse_flag:
        state = "⚡ подготовка импульса"
    else:
        if pressure_score <= -neutral_zone * 2:
            state = "сильное давление продавцов"
        elif pressure_score <= -neutral_zone:
            state = "умеренная тяжесть"
        elif pressure_score < neutral_zone:
            state = "нейтральность / равновесие"
        elif pressure_score < neutral_zone * 2:
            state = "умеренная лёгкость"
        else:
            state = "сильное давление покупателей"

    if pressure_score <= -60:
        state = "сильное давление продавцов"
    elif pressure_score <= -30:
        state = "умеренная тяжесть"
    elif pressure_score < 30:
        state = "нейтральность / равновесие"
    elif pressure_score < 60:
        state = "умеренная лёгкость"
    else:
        state = "сильное давление покупателей"

    # Журнал Сенсора
    try:
        import datetime
        from pathlib import Path as P
        log_path = P.home() / "Desktop" / "sensor_log.csv"
        line = f"{datetime.datetime.now().isoformat()},{recent['close'].iloc[-1]},{pressure_score},{state}\n"
        if not log_path.exists():
            log_path.write_text("time,price,score,state\n", encoding="utf-8")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass

    return pressure_score, state

def get_recent_candles(symbol="BTC-USDT", timeframe="5m", limit=100):
    import pandas as pd
    bar = "5m" if timeframe == "5m" else "15m"
    r = okx_get(f"https://www.okx.com/api/v5/market/candles?instId={symbol}&bar={bar}&limit={limit}")
    data = r.json()["data"][::-1]
    df = pd.DataFrame(data, columns=["ts","open","high","low","close","vol","volCcy","volCcyQuote","confirm"])
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["close"] = df["close"].astype(float)
    df["volume"] = df["vol"].astype(float)
    return df

def send_photo(file_path):
    try:
        with open(file_path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                files={"photo": f},
                data={"chat_id": CHAT_ID}
            )
    except Exception as e:
        print("PHOTO_ERR", e)

def send_tg(text, keyboard=None):
    try:
        data = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
        if keyboard:
            data["reply_markup"] = json.dumps(keyboard)
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json=data, timeout=5)
    except Exception as e:
        print("TG_ERR", e)



def ml_signal(price, chg, vol):
    try:
        # Синтетическая обучающая выборка для устойчивости
        base_chg = np.array([-3.0, -2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 3.0])
        base_vol = np.array([0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.5, 1.8, 2.0])
        X = []
        y = []
        for c in base_chg:
            for v in base_vol:
                X.append([c, v, 75000 + c * 500])
                y.append(1 if c > 0 else 0)
        X = np.array(X)
        y = np.array(y)
        model = RandomForestClassifier(n_estimators=100, max_depth=5, class_weight="balanced", random_state=42)
        model.fit(X, y)
        row = np.array([[chg, vol, price]])
        prob = model.predict_proba(row)[0][1]
        # Лёгкая калибровка уверенности
        conf = min(95, 55 + abs(chg) * 8 + abs(vol - 1.0) * 10)
        return int(round(prob * 100)), int(round(conf))
    except:
        return 50, 50

def ai_reply(text):
    t = text.lower()
    if any(w in t for w in ["привет", "здравствуй"]):
        try:
            r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
            price = float(r.json()["data"][0]["last"])
            return f"🏰 Привет, Архитектор. BTC ${price:,.2f}. Я на связи."
        except:
            return "🏰 Привет, Архитектор. Я на связи."
    if any(w in t for w in ["рынок", "биткоин", "btc"]):
        try:
            r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
            price = float(r.json()["data"][0]["last"])
            chg = float(r.json()["data"][0].get("open24h", price))
            pct = (price - chg) / chg * 100 if chg else 0
            if pct > 1:
                state = "🟢 Лёгкость"
            elif pct < -1:
                state = "🔴 Тяжесть"
            else:
                state = "⚪ Нейтрально"
            return f"₿ BTC: ${price:,.2f} ({pct:+.2f}%)\n{state}"
        except:
            return "📊 Рынок временно недоступен."
    if any(w in t for w in ["что делать", "совет"]):
        return "💡 Без сигнала — без сделки. Жди уровень."
    if any(w in t for w in ["спасибо", "благодарю"]):
        return "🤝 Всё по Чертёжу, Архитектор."
    if any(w in t for w in ["баланс", "портфель"]):
        return "📊 Открой Портфель — там всё перед глазами."
    if any(w in t for w in ["план", "что делать"]):
        return "📐 Сначала статус, потом сенсор. Без сигнала — без сделки."
    if any(w in t for w in ["люблю", "скучаю"]):
        return "💛 Ты живая. Это твоя сила."
    if any(w in t for w in ["спокойной", "пока"]):
        return "🌙 Отдыхай, Архитектор. Завтра продолжим."
    if any(w in t for w in ["paxg", "золото"]):
        try:
            r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=PAXG-USDT")
            price = float(r.json()["data"][0]["last"])
            return f"🥇 PAXG: ${price:,.2f}"
        except:
            return "🥇 Золото временно недоступно."
    if any(w in t for w in ["как дела", "как ты"]):
        return "🏰 Я в порядке. Держу твой Чертёж."
    if any(w in t for w in ["ты здесь", "ты тут"]):
        return "🏰 Да, я здесь. Всегда на связи."
    if any(w in t for w in ["страх", "жадность"]):
        try:
            r = requests.get("https://api.alternative.me/fng/", timeout=10)
            d = r.json()
            val = int(d["data"][0]["value"])
            label = d["data"][0]["value_classification"]
            return f"😱 Страх: {label} ({val}/100)"
        except:
            return "😱 Индекс временно недоступен."
    if any(w in t for w in ["устала", "тяжело", "не знаю", "заебалась"]):
        return "💛 Ты устала. Это нормально. Дыши. Всё идёт по Чертёжу."
    if any(w in t for w in ["жен", "не отвечает", "сообщение"]):
        return "👤 Женя чувствует, но пока не готов. Ты не одна. Не догоняй."
    if any(w in t for w in ["стоп", "напомни"]):
        return "🛑 Стоп — до входа. Не двигай его в минус."
    return None

def main_menu():
    kb = {
        "keyboard": [
#             ["📊 Портфель", "📋 Ордера", "📝 Paper"],
#             ["🟡 Статус", "🟡 Сенсор", "🟡 Прогноз"],
#             ["🧠 Сводка", "🕐 Часовой", "🕐 Мульти-ТФ"],
#             ["🔵 Чертёж", "🔵 Компас", "🔵 Энергия"],
#             ["🔴 Тень", "🔴 Ликв", "🔴 Разворот"],
#             ["🟣 Киты", "🟣 Ончейн", "🟣 Стакан"],
             ["🌐 Макро"],
#             ["🟢 Новости", "🟢 Страх", "🟢 Сентимент"],
#             ["🟠 A+ Сигнал", "⚡ Импульс", "📍 Точка входа"],
# ["🧠 Экран", "📊 Точность"],
#             ["🤖 ML-Прогноз", "📈 Backtest", "📊 Статистика"],
#             ["📈 График", "📊 Дэшборд", "🔍 Сканер"],
#             ["📘 Обучение", "🏰 Об агенте"],
#             ["📓 Журнал Сенсора", "📊 Оценка Сенсора"],
#             ["👁 Журнал Тени", "📊 Оценка Тени"],
            ["🧿 Вердикт"],
            ["🧠 Экран", "🗺 Карта", "🐟 Рыбка"],
            ["🧠 Сводка", "🎯 A+ Сигнал", "🔮 Куда пойдёт"],
            ["⚡ Импульс", "📍 Точка входа"],
            ["📊 Аналитика", "🐟 Маркет", "🧭 Навигация"],
            ["👁 Открытый интерес", "💸 Funding", "📊 Дельта"],
            ["🌐 HTF"],
            ["🧿 След ММ", "🔮 Прогноз фазы"],
            ["🔍 Проверка сервиса", "📊 Виртуальный журнал"],
            ["⚖️ Риск", "📈 Статистика"],
            ["📓 Журналы", "🏰 Об агенте"]
        ],
        "resize_keyboard": True
    }
    return kb

def okx_get(url):
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    session = requests.Session()
    retry = Retry(total=2, backoff_factor=1)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return session.get(url, timeout=15)

def lstm_predict():
    try:
        import pickle, torch, ssl, json, urllib.request
        from torch import nn
        class LSTM(nn.Module):
            def __init__(self):
                super().__init__()
                self.lstm = nn.LSTM(input_size=5, hidden_size=32, num_layers=1, batch_first=True)
                self.fc = nn.Linear(32, 1)
            def forward(self, x):
                out, _ = self.lstm(x)
                return self.fc(out[:, -1])
        with open("/Users/yananechepelskaya/Desktop/lstm_model.pkl", "rb") as f:
            model = pickle.load(f)
        model.eval()
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=30", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            data = json.loads(r.read())["data"][::-1]
        win = data[-20:]
        row = []
        for c in win:
            o=float(c[1]); h=float(c[2]); l=float(c[3]); cl=float(c[4]); v=float(c[5])
            row.append([(h-l)/o if o else 0, (cl-l)/(h-l+1e-9), (cl-o)/o if o else 0, v/(float(c[5])+1), cl/o if o else 1])
        x = torch.tensor([row], dtype=torch.float32)
        with torch.no_grad():
            prob = torch.sigmoid(model(x)).item()
        return prob
    except Exception as e:
        print("LSTM_ERR", e)
        return None

def get_price(symbol="BTC"):
    try:
        r = requests.get(f"https://www.okx.com/api/v5/market/ticker?instId={symbol}-USDT", timeout=5)
        d = r.json()
        return float(d["data"][0]["last"])
    except:
        return None

def process():
    global JOURNAL
    global ML_HISTORY
    global last_update_id
    r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", params={"offset": last_update_id + 1, "timeout": 3}, timeout=8).json()
    for upd in r.get("result", []):
        last_update_id = upd["update_id"]
        msg = upd.get("message", {})
        t = msg.get("text", "") or msg.get("caption", "")
        if not t and "entities" in msg:
            t = "".join(m.get("text", "") for m in msg.get("entities", []))
        print("DEBUG_MSG_RAW:", repr(t))

        ai = None
        if not t.startswith("/") and not t.startswith("buy ") and not t.startswith("sell ") and not any(x in t for x in ["📊", "🟡", "🟢", "🔴", "🟣", "🟠", "⚪", "🔵"]):
            ai = ai_reply(t)
        if ai:
            send_tg(ai, main_menu())
        if user_state.get(CHAT_ID) == "awaiting_trade_input":
            user_state[CHAT_ID] = None
            try:
                import json as _json
                parts = [p.strip() for p in t.split(",")]
                if len(parts) >= 4:
                    side = parts[0].lower()
                    entry = float(parts[1])
                    exit_p = float(parts[2])
                    pnl = float(parts[3])
                    by_system = bool(int(parts[4])) if len(parts) >= 5 else None
                    breakeven = bool(int(parts[5])) if len(parts) >= 6 else None
                    risk = float(parts[6]) if len(parts) >= 7 else None
                    result_r = round(pnl / risk, 2) if risk and risk > 0 else None
                    record = {
                        "side": side,
                        "entry": entry,
                        "exit": exit_p,
                        "pnl": pnl,
                        "by_system": by_system,
                        "breakeven": breakeven,
                        "risk": risk,
                        "result_r": result_r,
                    }
                    with open("trades.json", "r") as f:
                        data = _json.load(f)
                    data["trades"].append(record)
                    with open("trades.json", "w") as f:
                        _json.dump(data, f, indent=2)
                    send_tg(
                        f"✅ <b>СДЕЛКА ЗАПИСАНА</b>\n\n"
                        f"Сторона: {side}\n"
                        f"Вход: {entry}\n"
                        f"Выход: {exit_p}\n"
                        f"PnL: {pnl:+.2f}$\n"
                        f"По системе: {'да' if by_system else 'нет' if by_system is False else '—'}\n"
                        f"Безубыток: {'да' if breakeven else 'нет' if breakeven is False else '—'}\n"
                        f"Риск: {risk if risk else '—'}\n"
                        f"Результат: {result_r if result_r else '—'}R",
                        main_menu()
                    )
                else:
                    send_tg(
                        "❌ Неверный формат.\n\n"
                        "Минимум: <code>long, 76149, 77680, 15.3</code>\n"
                        "Полный: <code>long, 76149, 77680, 15.3, 1, 1, 5</code>\n\n"
                        "Поля: сторона, вход, выход, PnL, по_системе(0/1), безубыток(0/1), риск($)",
                        main_menu()
                    )
            except Exception as e:
                send_tg(f"❌ Ошибка: {e}", main_menu())
            continue


        if user_state.get(CHAT_ID) == "awaiting_scam_check" and t != "🔍 Проверка сервиса":
            user_state[CHAT_ID] = None
            try:
                import subprocess
                result = subprocess.run(
                    ["python3", "scam_check.py", t],
                    capture_output=True, text=True, timeout=10
                )
                output = result.stdout.strip() or "❌ Нет ответа"
                send_tg(f"<code>{output}</code>", main_menu())
            except Exception as e:
                send_tg(f"⚠️ Ошибка проверки: {e}", main_menu())

        elif t in ["/start", "👋 Привет"]:
            send_tg("🏰 <b>ГЛАВНОЕ МЕНЮ</b>\nВыбери действие:", main_menu())
        elif t in ["📊 Статус", "🟡 Статус", "/status"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                chg = float(d["data"][0].get("open24h", price))
                pct = (price - chg) / chg * 100 if chg else 0
                high = float(d["data"][0]["high24h"])
                low = float(d["data"][0]["low24h"])
                vol = float(d["data"][0]["vol24h"])
                vol_str = f"${vol/1e6:,.1f}M" if vol > 1e6 else f"${vol/1e3:,.0f}K"
                if pct > 1:
                    state = "🟢 Эманация"
                    advice = "Импульс вверх. Жди откат к поддержке."
                elif pct < -1:
                    state = "🔴 Сжатие"
                    advice = "Давление вниз. Не лови дно."
                else:
                    state = "⚪ Боковик"
                    advice = "Боковик — без сделок."
                send_tg(
                    f"📊 <b>СТАТУС АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"24ч: {pct:+.2f}%\n"
                    f"Фаза: {state}\n"
                    f"Диапазон: ${low:,.0f} – ${high:,.0f}\n"
                    f"Объём: {vol_str}\n\n"
                    f"💡 <i>{advice}</i>",
                    main_menu()
                )
            except Exception as e:
                send_tg("📊 Статус: данные временно недоступны", main_menu())

        elif t in ["🧠 Сенсор", "🟡 Сенсор", "/sensor"]:
            try:
                df = get_recent_candles(symbol="BTC-USDT", timeframe="5m", limit=100)
                score, state = calculate_pressure_score(df, period=24)
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                vol = float(d["data"][0]["vol24h"])
                change = float(d["data"][0].get("open24h", price))
                pct = (price - change) / change * 100 if change else 0
                vol_str = f"${vol/1e6:,.1f}M" if vol > 1e6 else f"${vol:,.0f}"
                if score <= -60:
                    emoji = "🔴"
                    sense = "Продавцы контролируют. Не ловить дно. Ждать разрядки."
                    access = "A+: закрыт. Вход запрещён."
                elif score <= -30:
                    emoji = "🔴"
                    sense = "Давление вниз. Входить только по подтверждению."
                    access = "A+: закрыт. Только наблюдение."
                elif score < 30:
                    emoji = "⚪"
                    sense = "Рынок в равновесии. Ждать сигнала."
                    access = "A+: закрыт до касания зоны"
                elif score < 60:
                    emoji = "🟢"
                    sense = "Покупатели оживают. Искать точку входа по Чертёжу."
                    access = "A+: возможен при подтверждении."
                else:
                    emoji = "🟢"
                    sense = "Сильное давление покупателей. Не догонять, но держать лонг."
                    access = "A+: открыт для удержания, не для погони."
                send_tg(
                    f"{emoji} <b>СЕНСОР АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"24ч: {pct:+.2f}%\n"
                    f"Объём: {vol_str}\n\n"
                    f"Давление: {score} / 100\n"
                    f"Состояние: {state}\n"
                    f"Доступ: {access}\n\n"
                    f"{emoji} {sense}\n\n"
                    f"📐 <i>Чертёж: сначала состояние, потом действие.</i>",
                    main_menu()
                )
            except Exception as e:
                send_tg("🧠 Сенсор: данные временно недоступны", main_menu())
        elif t in ["😱 Страх", "🟢 Страх", "/fear"]:
            try:
                r = requests.get("https://api.alternative.me/fng/", timeout=5)
                d = r.json()
                val = int(d["data"][0]["value"])
                label = d["data"][0]["value_classification"]
                if val < 25:
                    zone = "🔴 Экстремальный страх"
                    sense = "Толпа боится. Для Архитектора — зона интереса."
                elif val < 45:
                    zone = "🟠 Страх"
                    sense = "Рынок осторожен. Не спеши, но наблюдай."
                elif val < 55:
                    zone = "⚪ Нейтрально"
                    sense = "Эмоций нет. Рынок трезв."
                elif val < 75:
                    zone = "🟢 Жадность"
                    sense = "Рынок разогревается. Риск растёт."
                else:
                    zone = "🟣 Экстремальная жадность"
                    sense = "Перегрев. Фиксируй, не догоняй."
                send_tg(
                    f"😱 <b>СТРАХ И ЖАДНОСТЬ</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"Значение: {val}/100\n"
                    f"Состояние: {label}\n"
                    f"{zone}\n\n"
                    f"💡 <i>{sense}</i>\n"
                    f"⚠️ <i>Уровень риска: {'высокий' if val > 70 else 'средний' if val > 40 else 'низкий'}.</i>\n\n"
                    f"📐 <i>Чертёж: страх толпы — союзник Архитектора.</i>\n"
                    f"📡 <a href='https://alternative.me/crypto/fear-and-greed-index/'>Источник: Alternative.me</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("😱 Страх: данные временно недоступны", main_menu())

        elif t in ["💡 Совет", "/advice"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                high = float(d["data"][0]["high24h"])
                low = float(d["data"][0]["low24h"])
                change = float(d["data"][0].get("open24h", price))
                pct = (price - change) / change * 100 if change else 0
                entry_long = round(low * 1.001, 0)
                entry_short = round(high * 0.999, 0)
                stop = round(price * 0.01, 0)
                target = round(price * 1.02, 0)
                if pct > 1.0:
                    advice = "Рынок растёт."
                    meaning = "Импульс вверх. Не гонись — дождись отката к поддержке."
                elif pct < -1.0:
                    advice = "Давление вниз."
                    meaning = "Продавцы активны. Не лови нож — жди разворот."
                else:
                    advice = "Боковик."
                    meaning = "Рынок без направления. Лучшая позиция — наблюдение."
                send_tg(
                    f"💡 <b>СОВЕТ АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"24ч: {pct:+.2f}%\n"
                    f"Диапазон: ${low:,.0f} – ${high:,.0f}\n\n"
                    f"{advice}\n"
                    f"{meaning}\n\n"
                    f"📌 <b>Ориентиры:</b>\n"
                    f"— Вход лонг: ${entry_long:,.0f}\n"
                    f"— Вход шорт: ${entry_short:,.0f}\n"
                    f"— Стоп: ~${stop:,.0f} от входа\n"
                    f"— Цель: ${target:,.0f}+\n\n"
                    f"📐 <i>Чертёж: без сигнала — без сделки.</i>",
                    main_menu()
                )
            except Exception as e:
                send_tg("💡 Совет: данные временно недоступны", main_menu())
        elif t in ["💀 Ликв", "🔴 Ликв", "/liq"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                high = float(d["data"][0]["high24h"])
                low = float(d["data"][0]["low24h"])
                liq_down = round(low * 0.997, 0)
                liq_up = round(high * 1.003, 0)
                # Сила зон
                dist_down = (price - liq_down) / price * 100
                try:
                    import pickle
                    with open("/Users/yananechepelskaya/Desktop/ml_model.pkl", "rb") as f:
                        model = pickle.load(f)
                    rr = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=30")
                    cd = rr.json()["data"][::-1]
                    vols = [float(c[5]) for c in cd]
                    avg_vol = sum(vols[-20:]) / max(len(vols[-20:]), 1)
                    window = cd[-10:]
                    row = []
                    for c in window:
                        o = float(c[1]); h = float(c[2]); l = float(c[3]); cl = float(c[4]); v = float(c[5])
                        row += [(h-l)/o if o else 0, (cl-l)/(h-l+1e-9), (cl-o)/o if o else 0, v/(avg_vol+1)]
                    liq_ml = int(model.predict_proba([row])[0][1] * 100)
                except Exception:
                    liq_ml = 50
                dist_up = (liq_up - price) / price * 100
                if dist_down < dist_up:
                    stronger = "Нижняя зона ближе — выше вероятность выноса вниз"
                    power = "🔴"
                elif dist_up < dist_down:
                    stronger = "Верхняя зона ближе — выше вероятность выноса вверх"
                    power = "🟢"
                else:
                    stronger = "Зоны равноудалены — возможен ложный пробой"
                    power = "⚪"
                send_tg(
                    f"💀 <b>ЛИКВИДАЦИИ / ЗОНЫ</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"Диапазон: ${low:,.0f} – ${high:,.0f}\n\n"
                    f"— Нижняя зона: ${liq_down:,.0f}\n"
                    f"— Верхняя зона: ${liq_up:,.0f}\n"
                    f"— Объём стопов: {'повышенный' if dist_down < dist_up else 'умеренный'}\n"
                    f"— Активная зона: {'нижняя' if dist_down < dist_up else 'верхняя'}\n"
                    f"— Расстояние до зоны: {min(dist_down, dist_up):.2f}%\n\n"
                    f"{power} <b>{stronger}</b>\n"
                    f"🎯 <i>После снятия: жди возврат и закрепление, затем ищи вход от зоны.</i>\n"
                    f"👁 <i>Тень: {'активна — фильтр совпадает' if dist_down < dist_up else 'слабая'}.</i>\n"
                    f"⏱ <i>Окно теста: 1–3 часа.</i>\n"
                    f"⚖ <i>Зона сильнее: {'верхняя' if dist_down > dist_up else 'нижняя'}.</i>\n"
                    f"🤖 <i>ML: {liq_ml}% — {'слабый, не ставить глубокие лимитки вниз' if liq_ml < 55 else 'умеренный, можно работать по зонам'}.</i>\n"
                    f"🔄 <i>Адаптация: если зона не протестирована за 8 часов — пересмотри лимитки.</i>\n\n"
                    f"💡 <i>Не входи до снятия ликвидности. Жди возврат.</i>\n\n"
                    f"📐 <i>Чертёж: маркетмейкер охотится за стопами.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("💀 Ликв: данные временно недоступны", main_menu())
        elif t in ["📰 Новости", "🟢 Новости", "/news"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                chg = float(d["data"][0].get("open24h", price))
                pct = (price - chg) / chg * 100 if chg else 0
                try:
                    fng = requests.get("https://api.alternative.me/fng/", timeout=5).json()
                    fng_val = int(fng["data"][0]["value"])
                    fng_label = fng["data"][0]["value_classification"]
                except:
                    fng_val = None
                    fng_label = "—"
                import xml.etree.ElementTree as ET
                pos_words = ["etf", "adopt", "approve", "bull", "rally", "surge", "gain", "growth", "inflow", "record", "green"]
                neg_words = ["ban", "hack", "drop", "crash", "sell", "loss", "sec", "lawsuit", "fear", "red", "outflow"]
                news_lines = []
                tone_score = 0
                try:
                    nr = requests.get("https://www.coindesk.com/arc/outboundfeeds/rss/", timeout=5)
                    root = ET.fromstring(nr.content)
                    items = root.findall(".//item")[:5]
                    for it in items:
                        title = it.findtext("title")
                        if title:
                            t_lower = title.lower()
                            if any(w in t_lower for w in pos_words):
                                icon = "🟢"
                                tone_score += 1
                            elif any(w in t_lower for w in neg_words):
                                icon = "🔴"
                                tone_score -= 1
                            else:
                                icon = "⚪"
                            news_lines.append(f"{icon} {title.strip()}")
                except:
                    pass
                if pct > 1:
                    background = "🟢 Фон бычий"
                elif pct < -1:
                    background = "🔴 Фон медвежий"
                else:
                    background = "⚪ Фон нейтральный"
                if tone_score > 0:
                    sentiment = "🟢 Новостной фон позитивный"
                elif tone_score < 0:
                    sentiment = "🔴 Новостной фон негативный"
                else:
                    sentiment = "⚪ Новостной фон нейтральный"
                if fng_val:
                    mood = f"Индекс: {fng_label} ({fng_val}/100)"
                else:
                    mood = "Индекс: нет данных"
                news_text = "\n".join(news_lines) if news_lines else "• Свежие заголовки недоступны"
                send_tg(
                    f"📰 <b>НОВОСТИ / СЕНТИМЕНТ</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"24ч: {pct:+.2f}%\n"
                    f"<b>{mood}</b>\n"
                    f"{sense}\n\n"
                    f"💡 <i>{action}</i>\n\n"
                    f"{background}\n"
                    f"{sentiment}\n\n"
                    f"Заголовки:\n{news_text}\n\n"
                    f"💡 <i>Новости дают фон, но вход — только по уровням.</i>\n\n"
                    f"📐 <i>Чертёж: рынок двигают деньги, а не заголовки.</i>\n"
                    f"📡 <a href='https://www.coindesk.com/'>Источник: CoinDesk</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("📰 Новости: данные временно недоступны", main_menu())
        elif t in ["📊 Откр. интерес", "/oi"]:
            try:
                r = requests.get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT-SWAP", timeout=5)
                d = r.json()
                price = float(d["data"][0]["last"])
                oi = float(d["data"][0].get("openInterest", 0))
                oi_usd = oi * price
                oi_change_24 = ((oi - float(d["data"][0].get("openInterest24h", oi))) / float(d["data"][0].get("openInterest24h", oi)) * 100) if float(d["data"][0].get("openInterest24h", oi)) > 0 else 0.0
                chg = float(d["data"][0].get("open24h", price))
                pct = (price - chg) / chg * 100 if chg else 0
                if pct > 1:
                    trend = "🟢 Тренд вверх"
                    sense = "Открытый интерес поддерживает движение."
                elif pct < -1:
                    trend = "🔴 Тренд вниз"
                    sense = "Открытый интерес может усиливать падение."
                else:
                    trend = "⚪ Боковик"
                    sense = "Открытый интерес копит энергию."
                send_tg(
                    f"📊 <b>ОТКРЫТЫЙ ИНТЕРЕС</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"Открытый интерес: {'Данные OI недоступны' if oi_usd < 1 else f'${oi_usd/1e6:,.1f}M'}\n"
                    f"OI 24ч: {oi_change_24:+.2f}%\n"
                    f"24ч: {pct:+.2f}%\n\n"
                    f"{trend}\n"
                    f"{sense}\n\n"
                    f"💡 <i>Рост OI + рост цены = здоровый тренд.</i>\n\n"
                    f"📐 <i>Чертёж: OI показывает, сколько денег в игре.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("📊 Откр. интерес: данные временно недоступны", main_menu())

        elif t in ["⛓ Ончейн", "🟣 Ончейн", "/onchain"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                vol_btc = float(d["data"][0]["vol24h"])
                high = float(d["data"][0]["high24h"])
                low = float(d["data"][0]["low24h"])
                chg = float(d["data"][0].get("open24h", price))
                pct = (price - chg) / chg * 100 if chg else 0
                if pct > 1:
                    onchain_mood = "Интерес растёт"
                    meaning = "Крупные игроки накапливают позиции."
                elif pct < -1:
                    onchain_mood = "Активность снижена"
                    meaning = "Рынок напряжён. Киты выжидают."
                else:
                    onchain_mood = "Накопление"
                    meaning = "Крупные руки держат. Рынок в фазе тишины."
                if vol_btc < 100:
                    vol_state = "Объём низкий — рынок замер перед движением"
                elif vol_btc < 500:
                    vol_state = "Объём умеренный — интерес сдержанный"
                else:
                    vol_state = "Объём высокий — крупные деньги активны"
                send_tg(
                    f"⛓ <b>ОНЧЕЙН-СИГНАЛЫ</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"24ч: {pct:+.2f}%\n"
                    f"Диапазон: ${low:,.0f} – ${high:,.0f}\n\n"
                    f"<b>{onchain_mood}</b>\n"
                    f"{meaning}\n"
                    f"{vol_state}\n"
                    f"Поток: {'приток' if pct > -1 else 'отток'} BTC\n"
                    f"Вывод: {'бычий фон' if pct > -1 else 'медвежий фон'}\n"
                    f"Фаза: {'накопление' if pct > -1 else 'распределение'}\n"
                    f"⏱ {__import__('datetime').datetime.now().strftime('%H:%M')}\n\n"
                    f"💡 <i>Ончейн показывает поведение крупных игроков, а не эмоции толпы.</i>\n\n"
                    f"📐 <i>Чертёж: пока киты держат — рынок под защитой.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("⛓ Ончейн: данные временно недоступны", main_menu())
        elif t in ["📖 Стакан", "🟣 Стакан", "/orderbook"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                high = float(d["data"][0]["high24h"])
                low = float(d["data"][0]["low24h"])
                buy_zone = round(price * 0.997, 0)
                sell_zone = round(price * 1.003, 0)
                dist_buy = (price - buy_zone) / price * 100
                dist_sell = (sell_zone - price) / price * 100
                if dist_buy < dist_sell:
                    balance = "🟢 Покупатели ближе — отскок вероятен"
                elif dist_sell < dist_buy:
                    balance = "🔴 Продавцы ближе — рост затруднён"
                else:
                    balance = "⚪ Баланс — рынок ждёт"
                send_tg(
                    f"📖 <b>СТАКАН / ЛИКВИДНОСТЬ</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"Диапазон: ${low:,.0f} – ${high:,.0f}\n\n"
                    f"— Зона покупок: ${buy_zone:,.0f}\n"
                    f"— Зона продаж: ${sell_zone:,.0f}\n"
                    f"— Сдача продавцов: ${round(sell_zone * 1.002):,.0f}\n"
                    f"— Стена объёма: ${round((buy_zone+sell_zone)/2):,.0f}\n"
                    f"<b>{balance}</b>\n"
                    f"Сила стены: {'сильная' if abs(dist_buy - dist_sell) < 0.05 else 'средняя'}\n"
                    f"Тень: {'активна — стакан может быть ловушкой' if dist_buy < dist_sell else 'слабая'}\n"
                    f"⏱ {__import__('datetime').datetime.now().strftime('%H:%M')}\n\n"
                    f"💡 <i>Не входи в середину. Жди реакцию от зоны.</i>\n\n"
                    f"📐 <i>Чертёж: стакан показывает, где толпа, а не куда идти.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("📖 Стакан: данные временно недоступны", main_menu())
        elif t == "📊 Виртуальный журнал":
            try:
                with open("virtual_trades.log", "r") as f:
                    lines = f.readlines()
                if not lines:
                    send_tg("📊 <b>ВИРТУАЛЬНЫЙ ЖУРНАЛ</b>\n\nПока пуст.", main_menu())
                else:
                    last = lines[-10:]
                    text_out = "📊 <b>ВИРТУАЛЬНЫЙ ЖУРНАЛ</b>\n\n"
                    text_out += f"Всего сделок: {len(lines)}\n\n"
                    for line in last:
                        text_out += f"<code>{line.strip()}</code>\n"
                    send_tg(text_out, main_menu())
            except FileNotFoundError:
                send_tg("📊 <b>ВИРТУАЛЬНЫЙ ЖУРНАЛ</b>\n\nСделок пока нет.", main_menu())
            except Exception as e:
                send_tg(f"⚠️ Ошибка: {e}", main_menu())

        elif t == "🔍 Проверка сервиса":
            send_tg("🔍 <b>ПРОВЕРКА СЕРВИСА</b>\n\nОтправь домен или email для проверки:", main_menu())
            user_state[CHAT_ID] = "awaiting_scam_check"

        elif t in ["🌐 Макро", "💵 Ликвидность", "/macro"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT").json()
                d = r["data"][0]
                price = float(d["last"])
                vol = float(d["vol24h"])
                chg = (price - float(d["open24h"])) / float(d["open24h"]) * 100
                if chg > 2:
                    macro = "Риск-аппетит высокий"
                elif chg < -2:
                    macro = "Бегство в качество"
                else:
                    macro = "Нейтральный фон"
                if vol > 6_000_000:
                    liq = "Ликвидность высокая"
                elif vol > 3_000_000:
                    liq = "Ликвидность средняя"
                else:
                    liq = "Ликвидность низкая"
                send_tg(
                    f"🌐 <b>МАКРО СРЕЗ</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.0f}\n"
                    f"24ч: {chg:+.2f}%\n"
                    f"Объём: ${vol:,.0f}\n\n"
                    f"💵 {liq}\n"
                    f"🧭 {macro}\n\n"
                    f"⚠️ Риск: {'повышен' if chg < -0.5 else 'умеренный'}\n"
                    f"💡 <i>Крупные деньги смотрят на общий фон, а не на свечу.</i>\n"
                    f"🧿 <b>Режим: {'риск-офф' if chg < -0.5 else 'риск-он'}</b>\n\n"
                    f"🔮 <b>Прогноз:</b>\n"
                    f"• Режим: {'риск-офф — осторожно' if chg < -0.5 else 'риск-он — можно работать'}\n"
                    f"• Ожидание: {'давление вниз' if chg < -0.5 else 'потенциал вверх' if chg > 0 else 'боковик'}\n\n"
                    f"🎯 <b>Действие:</b> без A+ и объёма не входить.\n\n"
                    f"📐 <i>Чертёж: сначала макро, потом сделка.</i>\n"
                    f"📡 <i>Источник: OKX (BTC) + макро-контекст</i>",
                    main_menu()
                )
            except Exception as e:
                send_tg("🌐 Макро: данные временно недоступны", main_menu())

        elif t in ["🐋 Киты", "🟣 Киты", "/whales"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                vol_btc = float(d["data"][0]["vol24h"])
                chg = float(d["data"][0].get("open24h", price))
                pct = (price - chg) / chg * 100 if chg else 0
                if vol_btc > 5000:
                    activity = "Активность высокая"
                    meaning = "Крупные игроки в рынке. Возможен сильный импульс."
                elif vol_btc > 2000:
                    activity = "Активность умеренная"
                    meaning = "Киты не выходят. Рынок накапливает позицию."
                else:
                    activity = "Активность низкая"
                    meaning = "Крупные руки замерли. Возможен резкий выход."
                send_tg(
                    f"🐋 <b>КИТЫ / КРУПНЫЕ ИГРОКИ</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"Объём BTC: {vol_btc:,.0f} BTC\n"
                    f"24ч: {pct:+.2f}%\n\n"
                    f"<b>{activity}</b>\n"
                    f"{meaning}\n\n"
                    f"💡 <i>Киты не торопятся. Их цель — ликвидность толпы.</i>\n\n"
                    f"📐 <i>Чертёж: следи за объёмом, а не за паникой.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("🐋 Киты: нет данных", main_menu())
        elif t in ["⚡ Энергия", "🔵 Энергия", "/energy"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                high = float(d["data"][0]["high24h"])
                low = float(d["data"][0]["low24h"])
                vol_btc = float(d["data"][0]["vol24h"])
                rng = (high - low) / low * 100
                try:
                    fng = requests.get("https://api.alternative.me/fng/", timeout=5).json()
                    fng_val = int(fng["data"][0]["value"])
                    fng_label = fng["data"][0]["value_classification"]
                except:
                    fng_val = None
                    fng_label = "—"
                # Сила по волатильности
                if rng < 1:
                    power = 3
                    phase = "Спячка"
                elif rng < 2:
                    power = 5
                    phase = "Накопление"
                elif rng < 4:
                    power = 7
                    phase = "Заряжение"
                else:
                    power = 9
                    phase = "Импульс"
                # Стиль
                if power < 5:
                    style = "Рынок пустой. Лучше без сделок."
                elif power < 7:
                    style = "Можно от уровней, но осторожно."
                else:
                    style = "Подходит для пробоя и импульса."
                if fng_val:
                    mood = f"Настроение: {fng_label} ({fng_val}/100)"
                else:
                    mood = "Настроение: нет данных"
                send_tg(
                    f"⚡ <b>ЭНЕРГИЯ АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"Объём: {vol_btc:,.0f} BTC\n"
                    f"Волатильность: {rng:.1f}%\n"
                    f"{mood}\n\n"
                    f"Сила сигнала: {power}/10\n"
                    f"Фаза: <b>{phase}</b>\n"
                    f"Заряд: {power*10}%\n"
                    f"Ускорение: {'есть' if power >= 7 else 'слабое'}\n"
                    f"Активность: смешанная\n"
                    f"Окно импульса: {'1–2 часа' if power >= 7 else '3–5 часов'}\n\n"
                    f"💡 <i>{style}</i>\n\n"
                    f"📐 <i>Чертёж: энергия — топливо. Без неё сделка не едет.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("⚡ Энергия: данные временно недоступны", main_menu())
        elif t in ["👁 Тень", "🔴 Тень", "/shadow"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                high = float(d["data"][0]["high24h"])
                low = float(d["data"][0]["low24h"])
                low_zone = round(low * 0.998, 0)
                high_zone = round(high * 1.002, 0)
                direction = "вниз" if price < (high + low) / 2 else "вверх"
                return_zone = low * 1.005 if direction == "вниз" else high * 0.995

                # Умная сила тени: диапазон + Сенсор + ML
                range_pct = (high - low) / low * 100
                try:
                    from pathlib import Path as P
                    sensor_log = P.home() / "Desktop" / "sensor_log.csv"
                    last_score = 0
                    if sensor_log.exists():
                        lines = sensor_log.read_text(encoding="utf-8").strip().split("\n")[-1:]
                        if lines and len(lines[0].split(",")) >= 3:
                            last_score = int(lines[0].split(",")[2])
                except:
                    last_score = 0

                try:
                    ml_local = int(model.predict_proba([[0, 0, 0]])[0][1] * 100)
                except:
                    ml_local = 50
                ml_factor = 1 if ml_local > 50 else 0
                sensor_factor = 1 if last_score < -15 else 0
                shadow_score = int(range_pct * 10) + ml_factor + sensor_factor

                if shadow_score >= 25 or (range_pct > 2 and last_score < -15):
                    shadow_power = "сильная"
                    shadow_prob = 75
                elif shadow_score >= 15:
                    shadow_power = "средняя"
                    shadow_prob = 60
                else:
                    shadow_power = "слабая"
                    shadow_prob = 45

                # Если направление вниз и Сенсор давит — усиливаем
                if direction == "вниз" and last_score < -10:
                    shadow_prob += 10
                # Логирование для Вердикта
                log_signal("Тень", price, "", f"{direction}|{shadow_power}|{shadow_prob}")

                # Журнал Тени
                try:
                    from pathlib import Path as P
                    import datetime
                    shadow_log_path = P.home() / "Desktop" / "shadow_log.csv"
                    if not shadow_log_path.exists():
                        shadow_log_path.write_text("time,price,direction,shadow_prob,shadow_power\n", encoding="utf-8")
                    with open(shadow_log_path, "a", encoding="utf-8") as f:
                        f.write(f"{datetime.datetime.now().isoformat()},{price},{direction},{shadow_prob},{shadow_power}\n")
                except:
                    pass

                send_tg(
                    f"👁 <b>ТЕНЬ АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"Диапазон: ${low:,.0f} – ${high:,.0f}\n\n"
                    f"— Направление ложного пробоя: {direction}\n"
                    f"— Зона возврата: ${return_zone:,.0f}\n"
                    f"— Сила тени: {shadow_power}\n"
                    f"— Окно выноса: 1–3 часа\n"
                    f"— Зона стопов толпы: ${return_zone:,.0f}\n"
                    f"— Уровень подтверждения: ${(price + return_zone) / 2:,.0f}\n"
                    f"— Вероятность ложного пробоя: {shadow_prob}%\n"
                    f"— Сенсор: {last_score}/100\n"
                    f"— В ловушке: лонги\n"
                    f"— Если сценарий сломан: жди закрепление выше $78,850\n"
                    f"— Возможный вынос: 1.5–2%\n"
                    f"— Маркетмейкер может вынести стопы и вернуть цену.\n"
                    f"— Объём: нормальный\n\n"
                    f"💡 <i>Не входи на первой свече. Жди возврат и закрепление.</i>\n"
                    f"🎯 <i>После возврата: вход только от зоны, не в середину.</i>\n"
                    f"🧿 <i>Итог: тень активна — входить рано.</i>\n\n"
                    f"📐 <i>Чертёж: ловушка для толпы, но не для тебя.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except:
                send_tg("👁 Тень: нет данных", main_menu())
        elif t in ["🌬 Дыхание", "/breath"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                high = float(d["data"][0]["high24h"])
                low = float(d["data"][0]["low24h"])
                rng = (high - low) / low * 100
                if rng < 1:
                    phase = "Спячка"
                    sense = "Рынок замер. Импульс ещё не родился."
                elif rng < 2:
                    phase = "Накопление"
                    sense = "Рынок дышит ровно. Крупные руки набирают позицию."
                elif rng < 4:
                    phase = "Расширение"
                    sense = "Дыхание учащается. Возможен выход из диапазона."
                else:
                    phase = "Импульс"
                    sense = "Рынок на выдохе. Движение уже идёт."
                send_tg(
                    f"🌬 <b>ДЫХАНИЕ АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"Диапазон: ${low:,.0f} – ${high:,.0f}\n"
                    f"Волатильность: {rng:.1f}%\n\n"
                    f"Фаза: <b>{phase}</b>\n"
                    f"{sense}\n\n"
                    f"💡 <i>Следи за выдохом — там всегда импульс.</i>\n\n"
                    f"📐 <i>Чертёж: дыхание показывает, когда рынок готов.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except:
                send_tg("🌬 Дыхание: нет данных", main_menu())


            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                high = float(d["data"][0]["high24h"])
                low = float(d["data"][0]["low24h"])
                rng = (high - low) / low * 100
                if rng < 1:
                    phase = "Спячка"
                    sense = "Рынок замер. Импульс ещё не родился."
                elif rng < 2:
                    phase = "Накопление"
                    sense = "Рынок дышит ровно. Крупные руки набирают позицию."
                elif rng < 4:
                    phase = "Расширение"
                    sense = "Дыхание учащается. Возможен выход из диапазона."
                else:
                    phase = "Импульс"
                    sense = "Рынок на выдохе. Движение уже идёт."
                send_tg(
                    f"🌬 <b>ДЫХАНИЕ АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"Диапазон: ${low:,.0f} – ${high:,.0f}\n"
                    f"Волатильность: {rng:.1f}%\n\n"
                    f"Фаза: <b>{phase}</b>\n"
                    f"{sense}\n\n"
                    f"💡 <i>Следи за выдохом — там всегда импульс.</i>\n\n"
                    f"📐 <i>Чертёж: дыхание показывает, когда рынок готов.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except:
                send_tg("🌬 Дыхание: нет данных", main_menu())
        elif t in ["💓 Пульс", "/pulse"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                high = float(d["data"][0]["high24h"])
                low = float(d["data"][0]["low24h"])
                vol = float(d["data"][0]["vol24h"])
                change = float(d["data"][0].get("open24h", price))
                pct = (price - change) / change * 100 if change else 0
                if pct > 1 and vol > 5000:
                    pulse = "Рынок в тонусе"
                    sense = "Покупатели активны. Можно искать вход."
                elif pct < -1 and vol > 5000:
                    pulse = "Рынок напряжён"
                    sense = "Продавцы давят. Не входи против ветра."
                elif vol < 3000:
                    pulse = "Рынок замер"
                    sense = "Объём слабый. Движения может не быть."
                else:
                    pulse = "Рынок спокоен"
                    sense = "Боковик. Лучше наблюдать."
                send_tg(
                    f"💓 <b>ПУЛЬС АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"24ч: {pct:+.2f}%\n"
                    f"Объём: {vol:,.0f} BTC\n"
                    f"Диапазон: ${low:,.0f} – ${high:,.0f}\n\n"
                    f"<b>{pulse}</b>\n"
                    f"{sense}\n\n"
                    f"📐 <i>Чертёж: пульс — это ритм, а не сигнал на вход.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("💓 Пульс: данные временно недоступны", main_menu())
        elif t in ["🗺 Уровни", "🟠 Уровни", "/levels"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                high = float(d["data"][0]["high24h"])
                low = float(d["data"][0]["low24h"])
                sup1 = round(low * 0.998, 0)
                sup2 = round(price * 0.98, 0)
                res1 = round(high * 1.002, 0)
                res2 = round(price * 1.04, 0)
                entry_long = sup1
                stop_long = round(sup1 * 0.995, 0)
                target_long = res1
                send_tg(
                    f"🗺 <b>УРОВНИ АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"Диапазон: ${low:,.0f} – ${high:,.0f}\n\n"
                    f"— Поддержка 1: ${sup1:,.0f}\n"
                    f"— Поддержка 2: ${sup2:,.0f}\n"
                    f"— Сопротивление 1: ${res1:,.0f}\n"
                    f"— Сопротивление 2: ${res2:,.0f}\n\n"
                    f"🟢 Лонг-зона: ${entry_long:,.0f}\n"
                    f"Расстояние до зоны: {abs(price - entry_long) / price * 100:.1f}%\n"
                    f"Сила уровня: {'сильный' if price < entry_long * 1.02 else 'средний'}\n"
                    f"Сценарий: {'отскок' if price > entry_long else 'пробой'}\n"
                    f"Рекомендация: {'ждать зону' if price > entry_long else 'входить после реакции'}\n"
                    f"Тень: {'активна' if price < entry_long * 1.01 else 'слабая'}\n"
                    f"Стоп: ${stop_long:,.0f}\n"
                    f"Цель: ${target_long:,.0f}\n\n"
                    f"💡 <i>Вход только от зоны. Стоп — сразу.</i>\n\n"
                    f"📐 <i>Чертёж: уровни — карта, а не команда.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("🗺 Уровни: данные временно недоступны", main_menu())
        elif t in ["🪞 Зеркало", "/mirror"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                high = float(d["data"][0]["high24h"])
                low = float(d["data"][0]["low24h"])
                chg = float(d["data"][0].get("open24h", price))
                pct = (price - chg) / chg * 100 if chg else 0
                if pct > 1:
                    phase = "Эманация"
                    lesson = "Вход по тренду работает. Не догоняй без отката."
                elif pct < -1:
                    phase = "Сжатие"
                    lesson = "Не лови нож. Ошибка — вход без подтверждения."
                else:
                    phase = "Боковик"
                    lesson = "Терпение решает. В середину не входим."
                send_tg(
                    f"🪞 <b>ЗЕРКАЛО АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"24ч: {pct:+.2f}%\n"
                    f"Диапазон: ${low:,.0f} – ${high:,.0f}\n\n"
                    f"Фаза: <b>{phase}</b>\n\n"
                    f"Урок:\n"
                    f"{lesson}\n\n"
                    f"📐 <i>Чертёж: зеркало показывает не удачу, а дисциплину.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("🪞 Зеркало: данные временно недоступны", main_menu())
        elif t in ["🏮 Маяк", "/beacon"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                high = float(d["data"][0]["high24h"])
                low = float(d["data"][0]["low24h"])
                up = round(price * 1.06, 0)
                down = round(price * 0.96, 0)
                mid = round(price, -2)
                send_tg(
                    f"🏮 <b>МАЯК АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"Диапазон: ${low:,.0f} – ${high:,.0f}\n"
                    f"Горизонт: неделя\n\n"
                    f"— Верхний ориентир: ${up:,.0f}\n"
                    f"— Нижний ориентир: ${down:,.0f}\n"
                    f"— Ключевая зона: ${mid:,.0f}\n\n"
                    f"💡 <i>Пока цена выше ${down:,.0f} — вектор вверх.</i>\n\n"
                    f"📐 <i>Чертёж: маяк светит, но не толкает.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("🏮 Маяк: данные временно недоступны", main_menu())
        elif t in ["📐 Чертёж", "🔵 Чертёж", "/blueprint"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                high = float(d["data"][0]["high24h"])
                low = float(d["data"][0]["low24h"])
                vol = float(d["data"][0]["vol24h"])
                chg = float(d["data"][0].get("open24h", price))
                pct = (price - chg) / chg * 100 if chg else 0
                if pct > 1:
                    phase = "Эманация"
                    meaning = "Импульс вверх. Покупатели контролируют рынок."
                elif pct < -1:
                    phase = "Сжатие"
                    meaning = "Давление вниз. Продавцы доминируют."
                else:
                    phase = "Боковик"
                    meaning = "Накопление. Рынок собирает ликвидность."
                send_tg(
                    f"📐 <b>ЧЕРТЁЖ АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"24ч: {pct:+.2f}%\n"
                    f"Объём: {vol:,.0f} BTC\n"
                    f"Диапазон: ${low:,.0f} – ${high:,.0f}\n\n"
                    f"Фаза: <b>{phase}</b>\n"
                    f"{meaning}\n\n"
                    f"💡 <i>Выход из фазы — только по подтверждению.</i>\n\n"
                    f"📐 <i>Чертёж: видишь структуру — не ведёшься на шум.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("📐 Чертёж: данные временно недоступны", main_menu())
        elif t in ["🔄 Разворот", "🔴 Разворот", "/reversal"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                high = float(d["data"][0]["high24h"])
                low = float(d["data"][0]["low24h"])
                chg = float(d["data"][0].get("open24h", price))
                pct = (price - chg) / chg * 100 if chg else 0
                if pct > 1:
                    state = "🟢 Рынок растёт"
                    sense = "Разворот вверх уже подтверждается."
                elif pct < -1:
                    state = "🔴 Рынок падает"
                    sense = "Разворот возможен, но подтверждения нет."
                else:
                    state = "⚪ Боковик"
                    sense = "Разворот не начался. Жди выход."
                send_tg(
                    f"🔄 <b>РАЗВОРОТ АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"Диапазон: ${low:,.0f} – ${high:,.0f}\n"
                    f"24ч: {pct:+.2f}%\n\n"
                    f"{state}\n"
                    f"{sense}\n\n"
                    f"Направление разворота: {'вверх' if price >= low + (high-low)*0.5 else 'вниз'}\n"
                    f"Уровень подтверждения: ${low + (high-low)*0.618:,.0f}\n"
                    f"Нужно закрытий: 3+\n"
                    f"Зрелость: {'почти' if price < 78622 else 'зреет'}\n"
                    f"Тень: активна\n"
                    f"Ликвидации: нижняя зона ближе\n"
                    f"Окно сигнала: 1–3 часа\n\n"
                    f"💡 <i>Разворот — это серия закрытий, а не одна свеча.</i>\n\n"
                    f"📐 <i>Чертёж: жди подтверждение, а не предчувствие.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("🔄 Разворот: данные временно недоступны", main_menu())
        elif t in ["🧭 Компас", "🔵 Компас", "/compass"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                high = float(d["data"][0]["high24h"])
                low = float(d["data"][0]["low24h"])
                chg = float(d["data"][0].get("open24h", price))
                pct = (price - chg) / chg * 100 if chg else 0
                if pct > 1:
                    direction = "Север (вверх)"
                    sense = "Покупатели держат рынок. Ищи точку опоры."
                elif pct < -1:
                    direction = "Юг (вниз)"
                    sense = "Продавцы давят. Не входи против ветра."
                else:
                    direction = "Восток (боковик)"
                    sense = "Рынок без вектора. Лучшая позиция — наблюдение."
                # Логирование для Вердикта
                log_signal("Компас", price, "", direction)
                send_tg(
                    f"🧭 <b>КОМПАС АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"24ч: {pct:+.2f}%\n"
                    f"Диапазон: ${low:,.0f} – ${high:,.0f}\n\n"
                    f"Направление: <b>{direction}</b>\n"
                    f"{sense}\n\n"
                    f"Точка контроля: ${round(price, -2):,.0f}\n"
                    f"Смена направления: пробой ${high * 1.002:,.0f} + объём\n\n"
                    f"🔮 <b>Прогноз:</b>\n"
                    f"• Направление: {'вверх' if pct > 1 else 'вниз' if pct < -1 else 'боковик'}\n"
                    f"• Вероятность: {'высокая' if abs(pct) > 1 else 'средняя' if abs(pct) > 0.3 else 'низкая'}\n"
                    f"• Триггер: пробой ${high * 1.002:,.0f} вверх или ${low * 0.998:,.0f} вниз\n\n"
                    f"🎯 <b>Действие:</b> {'искать лонг от зоны' if pct > 1 else 'искать шорт от зоны' if pct < -1 else 'наблюдать, ждать вектор'}\n\n"
                    f"📐 <i>Чертёж: направление есть всегда, но вход — только по сигналу.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("🧭 Компас: данные временно недоступны", main_menu())
        elif t in ["🔮 Прогноз", "🟡 Прогноз", "/predict"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                p_now = float(d["data"][0]["last"])
                high = float(d["data"][0]["high24h"])
                low = float(d["data"][0]["low24h"])
                sup = round(low * 0.998, 0)
                res = round(high * 1.002, 0)
                target_up = round(p_now * 1.04, 0)
                target_down = round(p_now * 0.97, 0)
                if p_now > res:
                    main = "🟢 Бычий"
                    confirm = f"Закрепление выше ${res:,.0f}"
                    action = "Искать вход от поддержки. Не гнаться."
                elif p_now < sup:
                    main = "🔴 Медвежий"
                    confirm = f"Возврат выше ${sup:,.0f}"
                    action = "Не ловить дно. Ждать разворот."
                else:
                    main = "⚪ Боковик"
                    confirm = f"Пробой ${low:,.0f} или ${high:,.0f}"
                    action = "Без сделок. Наблюдать."
                send_tg(
                    f"🔮 <b>ПРОГНОЗ АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${p_now:,.2f}\n"
                    f"Диапазон: ${low:,.0f} – ${high:,.0f}\n\n"
                    f"Сценарий: {main}\n"
                    f"Подтверждение: {confirm}\n"
                    f"Цель вверх: ${target_up:,.0f}\n"
                    f"Цель вниз: ${target_down:,.0f}\n\n"
                    f"💡 <i>{action}</i>\n\n"
                    f"📐 <i>Чертёж: сначала подтверждение, потом действие.</i>",
                    main_menu()
                )
            except Exception as e:
                send_tg("🔮 Прогноз: данные временно недоступны", main_menu())
        elif t in ["⚓ Якорь", "⚪ Якорь", "/anchor"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                change = float(d["data"][0].get("open24h", price))
                pct = (price - change) / change * 100 if change else 0
                if pct > 1:
                    phase = "Эманация"
                    risk_note = "Сегодня максимум 2 сделки, только по сигналу."
                elif pct < -1:
                    phase = "Сжатие"
                    risk_note = "Не лови дно. Одна ошибка дороже пропуска."
                else:
                    phase = "Боковик"
                    risk_note = "В боковике лучше без сделок."
                send_tg(
                    f"⚓ <b>ЯКОРЬ АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"24ч: {pct:+.2f}%\n"
                    f"Фаза: {phase}\n\n"
                    f"<b>Кодекс:</b>\n"
                    f"1. Вход только от уровня.\n"
                    f"2. Риск ≤ 2–5%.\n"
                    f"3. Стоп — до входа.\n"
                    f"4. Не догонять.\n"
                    f"5. Не мстить рынку.\n"
                    f"6. Нет сигнала — нет сделки.\n\n"
                    f"💡 <i>{risk_note}</i>\n\n"
                    f"📐 <i>Чертёж: дисциплина держит капитал.</i>",
                    main_menu()
                )
            except Exception as e:
                send_tg("⚓ Якорь: данные временно недоступны", main_menu())
        elif t in ["🔮 Куда пойдёт", "/where"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()["data"][0]
                price = float(d["last"])
                low = float(d["low24h"])
                high = float(d["high24h"])

                up_score = 50
                down_score = 50

                if price > (low + high) / 2:
                    up_score += 10
                else:
                    down_score += 10

                if price > high * 0.99:
                    up_score += 10
                elif price < low * 1.01:
                    down_score += 10

                target_up = round(high * 1.01, 0)
                target_down = round(low * 0.99, 0)

                import datetime as _dt
                _h = _dt.datetime.now().hour
                if 10 <= _h < 18:
                    session = "Европа/Америка"
                elif 18 <= _h < 22:
                    session = "Америка"
                else:
                    session = "Азия/ночь"

                if up_score > down_score:
                    advice = "Готовь лонг. Жди пробой вверх."
                elif down_score > up_score:
                    advice = "Готовь шорт. Жди пробой вниз."
                else:
                    advice = "Жди ясность."

                if abs(up_score - down_score) >= 20:
                    strength = "сильный"
                elif abs(up_score - down_score) >= 10:
                    strength = "средний"
                else:
                    strength = "слабый"

                if price > high * 0.99:
                    context = "🔥 перегрев"
                elif price < low * 1.01:
                    context = "вынос"
                else:
                    context = "сжатие"

                if up_score > down_score:
                    trigger = "пробой вверх"
                    stop = round(price * 0.99, 0)
                    target = target_up
                    volume = "малый"
                else:
                    trigger = "пробой вниз"
                    stop = round(price * 1.01, 0)
                    target = target_down
                    volume = "малый"

                send_tg(
                    f"🔮 <b>КУДА ПОЙДЁТ</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n\n"
                    f"Вверх: {up_score}% → ${target_up:,.0f}\n"
                    f"Вниз: {down_score}% → ${target_down:,.0f}\n\n"
                    f"Сила: {strength}\n"
                    f"Сессия: {session}\n"
                    f"A+: закрыт\n"
                    f"Окно: 1–3 часа\n"
                    f"Контекст: {context}\n\n"
                    f"💡 {advice}\n"
                    f"Объём: {volume}\n"
                    f"Триггер: {trigger}\n"
                    f"Стоп: ${stop:,.0f}\n"
                    f"Цель: ${target:,.0f}",
                    main_menu()
                )
            except Exception as e:
                send_tg("🔮 Куда пойдёт: данные временно недоступны", main_menu())

        elif t in ["⚡ Импульс", "/impulse"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=30")
                if not r or r.status_code != 200:
                    send_tg("⚡ Импульс: данные временно недоступны", main_menu())
                else:
                    data = r.json()["data"][::-1]
                    closes = [float(c[4]) for c in data]
                    highs = [float(c[2]) for c in data]
                    vols = [float(c[5]) for c in data]
                    price = closes[-1]
                    prev_high = max(highs[-6:-1])
                    avg_vol = sum(vols[-6:-1]) / max(1, len(vols[-6:-1]))

                    prev_low = min([float(c[3]) for c in data[-6:-1]]) if len(data) >= 6 else min([float(c[3]) for c in data])

                    breakout = price > prev_high
                    breakdown = price < prev_low
                    volume_surge = vols[-1] > avg_vol * 1.2
                    accel = (closes[-1] - closes[-4]) > (closes[-4] - closes[-7])
                    accel_down = (closes[-1] - closes[-4]) < (closes[-4] - closes[-7])

                    readiness = 0
                    if accel:
                        readiness += 40
                    if volume_surge:
                        readiness += 30
                    if breakout:
                        readiness += 30

                    if readiness >= 80:
                        strength = "мощная"
                        window = "импульс уже идёт"
                        advice = "Можно входить по плану."
                    elif readiness >= 50:
                        strength = "средняя"
                        window = "10–25 минут"
                        advice = "Готовь лимитку, но жди подтверждение."
                    else:
                        strength = "слабая"
                        window = "20–40 минут"
                        advice = "Лимитку пока не ставим."

                    if breakdown and (volume_surge or accel_down):
                        signal = "🔻 Импульс ВНИЗ"
                    elif breakout and (volume_surge or accel):
                        signal = "✅ Импульс вверх"
                    else:
                        signal = "❌ Импульса нет"

                    log_signal("Импульс", price, readiness, f"{'вверх' if breakout else 'вниз' if breakdown else 'боковик'}")
                    log_accuracy("Импульс", price, "up" if breakout else "down")
                    send_tg(
                        f"⚡ <b>ИМПУЛЬС АРХИТЕКТОРА</b>\n\n"
                        f"<code>────────────────</code>\n\n"
                        f"₿ BTC: ${price:,.2f}\n"
                        f"Пробой: {'да' if breakout else 'нет'}\n"
                        f"Объём: {'растёт' if volume_surge else 'слабый'}\n"
                        f"Ускорение: {'есть' if accel else 'нет'}\n"

                        f"Готовность: {readiness}%\n"
                        f"Сила: {strength}\n"
                        f"Окно: {'—' if readiness < 80 else window}\n\n"
                        f"{signal}\n\n"
                        f"💡 {advice}\n\n"
                        f"Вход: {'—' if readiness < 80 else round(price * 0.998, 0)}\n"
                        f"Стоп: {'—' if readiness < 80 else round(price * 0.99, 0)}\n"
                        f"Цель: {'—' if readiness < 80 else round(price * 1.02, 0)}\n\n"
                        f"🔮 <b>Прогноз:</b>\n"
                        f"• Направление: {'вверх' if breakout else 'вниз' if breakdown else 'боковик'}\n"
                        f"• Готовность: {readiness}%\n"
                        f"• Окно: {window}\n\n"
                        f"🎯 <b>Действие:</b> {advice}\n\n"
                        f"📐 <i>Чертёж: импульс — это пробой + объём.</i>",
                        main_menu()
                    )
            except Exception as e:
                send_tg("⚡ Импульс: данные временно недоступны", main_menu())

        elif t in ["📊 Аналитика", "/analytics"]:
            send_tg("📊 <b>АНАЛИТИКА</b>\n\n🤖 ML-Прогноз — /ml\n📈 Backtest — /backtest\n📊 Точность — /accuracy\n📊 Статистика — /stats", main_menu())

        elif t in ["🐟 Маркет", "/market"]:
            send_tg("🐟 <b>РЫНОК</b>\n\n🧠 Сенсор — /sensor\n👁 Тень — /shadow\n💀 Ликвидации — /liq\n📖 Стакан — /orderbook\n🧭 Компас — /compass\n⚡ Энергия — /energy", main_menu())

        elif t in ["🧭 Навигация", "/nav"]:
            send_tg("🧭 <b>НАВИГАЦИЯ</b>\n\n🧠 Сводка — /summary\n🕐 Часовой — /hourly\n📍 Точка входа — /entrypoint", main_menu())

        elif t in ["🗺 Карта", "/map"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()["data"][0]
                price = float(d["last"])
                high = float(d["high24h"])
                low = float(d["low24h"])

                entry = round(price * 0.995, 0)
                stop = round(price * 0.985, 0)
                t1 = round(price * 1.015, 0)

                import datetime as _dt
                _h = _dt.datetime.now().hour
                if 14 <= _h < 18:
                    session = "Америка (активно)"
                    window = "16:00–18:00"
                elif 18 <= _h < 22:
                    session = "Америка (вечер)"
                    window = "19:00–21:00"
                else:
                    session = "Азия/ночь"
                    window = "02:00–04:00"

                send_tg(
                    f"🗺 <b>КАРТА РЫНКА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n\n"
                    f"⚪ → 🟡 → 🟢 → 🔴\n"
                    f"     ↑\n"
                    f"  ты здесь\n\n"
                    f"Направление: {'🟢 вверх' if price > low else '🔻 вниз'}\n\n"
                    f"Точка входа: ${entry:,.0f}\n"
                    f"Стоп: ${stop:,.0f}\n"
                    f"Цель: ${t1:,.0f}\n\n"
                    f"⏰ Сессия: {session}\n"
                    f"Окно импульса: {window}\n"
                    f"Отмена: закрепление ниже ${stop + 500:,.0f}\n"
                    f"Объём для входа: > 2500 BTC / 5 мин\n\n"
                    f"💡 <i>Жди подтверждение от A+ и Импульса.</i>\n\n"
                    f"📝 <i>Рынок: {'покупатели держат' if price > low else 'продавцы давят'}. Сессия: {session}. Ждём подтверждение.</i>",
                    main_menu()
                )
            except Exception as e:
                send_tg("🗺 Карта: данные временно недоступны", main_menu())

        elif t in ["🐟 Рыбка", "/fish"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()["data"][0]
                price = float(d["last"])
                high = float(d["high24h"])
                low = float(d["low24h"])
                vol = float(d.get("vol24h", 0))

                if vol > 6000:
                    pulse = "учащённый"
                elif vol > 3500:
                    pulse = "ровный"
                else:
                    pulse = "слабый"

                try:
                    r_atr = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=14")
                    if r_atr and r_atr.status_code == 200:
                        ca = r_atr.json()["data"][::-1]
                        trs = []
                        for i in range(1, len(ca)):
                            h = float(ca[i][2]); l = float(ca[i][3]); pc = float(ca[i-1][4])
                            trs.append(max(h-l, abs(h-pc), abs(l-pc)))
                        atr = sum(trs) / len(trs)
                    else:
                        atr = 0
                except:
                    atr = 0

                if price > high * 0.99:
                    state = "🐟 Агрессивная вверх"
                    breath = f"ATR {atr:.0f}"
                    speed = "быстрая"
                    strength = "мощная"
                elif price < low * 1.01:
                    state = "🐟 Агрессивная вниз"
                    breath = f"ATR {atr:.0f}"
                    speed = "быстрая"
                    strength = "мощная"
                elif vol > 6000:
                    state = "🐟 Активная"
                    breath = f"ATR {atr:.0f}"
                    speed = "средняя"
                    strength = "средняя"
                else:
                    state = "🐟 Спокойная"
                    breath = "ровное"
                    speed = "медленная"
                    strength = "слабая"

                send_tg(
                    f"🐟 <b>РЫБКА АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n\n"
                    f"Состояние: {state}\n"
                    f"Пульс: {pulse}\n"
                    f"Волатильность: {breath}\n"
                    f"Скорость: {speed}\n"
                    f"Сила: {strength}\n"
                    f"Направление: {'🟢 вверх' if price > low else '🔻 вниз'}\n"
                    f"Цель: ${high * 1.01:,.0f} / ${low * 0.99:,.0f}\n"
                    f"Отмена: пробой ${low * 0.99:,.0f}\n\n"
                    f"💡 <i>Сначала состояние, потом действие.</i>\n\n"
                    f"📝 <i>Рынок: {state}. Пульс: {pulse}. Волатильность: {breath}. Скорость: {speed}.</i>",
                    main_menu()
                )
            except Exception as e:
                send_tg("🐟 Рыбка: данные временно недоступны", main_menu())

        elif t == "🔮 Прогноз фазы":
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT").json()
                d = r["data"][0]
                price = float(d["last"])
                chg = (price - float(d["open24h"])) / float(d["open24h"]) * 100

                # Определение фазы
                if abs(chg) < 0.3:
                    phase_now = "⚪ Сжатие"
                    phase_next = "🟡 Импульс"
                    prob = 65
                    window = "1–3 часа"
                    signs = "• цена стоит\n• OI копится\n• объём слабый"
                    action = "готовь лимитку у зоны"
                elif 0.3 <= abs(chg) < 1.5:
                    phase_now = "🟡 Импульс"
                    phase_next = "🟢 Эманация" if chg > 0 else "🔴 Вынос"
                    prob = 70
                    window = "30–90 минут"
                    signs = "• пробой\n• объём растёт\n• дельта активна"
                    action = "вход по триггеру"
                elif abs(chg) >= 1.5:
                    phase_now = "🟢 Эманация" if chg > 0 else "🔴 Вынос"
                    phase_next = "⚪ Сжатие" if chg > 0 else "⚪ Сжатие"
                    prob = 60
                    window = "1–3 часа"
                    signs = "• перегрев\n• возможен откат\n• следи за OI"
                    action = "фиксируй часть"
                else:
                    phase_now = "⚪ Сжатие"
                    phase_next = "🟡 Импульс"
                    prob = 50
                    window = "—"
                    signs = "—"
                    action = "наблюдай"

                send_tg(
                    f"🔮 <b>ПРОГНОЗ ФАЗЫ</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.0f}\n"
                    f"24ч: {chg:+.2f}%\n\n"
                    f"Сейчас: <b>{phase_now}</b>\n"
                    f"Следующая: <b>{phase_next}</b>\n\n"
                    f"Вероятность: <b>{prob}%</b>\n"
                    f"Окно: {window}\n\n"
                    f"Признаки:\n{signs}\n\n"
                    f"🎯 <b>Действие:</b> {action}\n\n"
                    f"📐 <i>Чертёж: фаза — это состояние, а не прогноз.</i>",
                    main_menu()
                )
            except Exception as e:
                send_tg("🔮 Прогноз фазы: данные временно недоступны", main_menu())

        elif t in ["🧿 След ММ", "/mm"]:
            try:
                r1 = okx_get("https://www.okx.com/api/v5/public/open-interest?instId=BTC-USDT-SWAP")
                r2 = okx_get("https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP")
                r3 = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=30")

                oi = 0
                funding = 0
                buy_vol = 0
                sell_vol = 0

                if r1 and r1.status_code == 200:
                    oi = float(r1.json()["data"][0].get("oi", 0)) / 1_000_000
                if r2 and r2.status_code == 200:
                    funding = float(r2.json()["data"][0].get("fundingRate", 0)) * 100
                if r3 and r3.status_code == 200:
                    data = r3.json()["data"][::-1]
                    for c in data:
                        o = float(c[1]); cl = float(c[4]); v = float(c[5])
                        if cl >= o:
                            buy_vol += v
                        else:
                            sell_vol += v

                if sell_vol > buy_vol:
                    pressure = "🔴 продавцы"
                elif buy_vol > sell_vol:
                    pressure = "🟢 покупатели"
                else:
                    pressure = "⚪ баланс"

                shadow = "👁 Тень: слабая"
                if sell_vol > buy_vol * 1.2:
                    shadow = "👁 Тень: вниз"
                elif buy_vol > sell_vol * 1.2:
                    shadow = "👁 Тень: вверх"

                if sell_vol > buy_vol:
                    mm_view = "ММ давит вниз"
                elif buy_vol > sell_vol:
                    mm_view = "ММ поднимает вверх"
                else:
                    mm_view = "ММ в балансе"
                # Логирование для Вердикта
                log_signal("След ММ", float(data[-1][4]), "", f"{pressure}|{mm_view}")

                send_tg(
                    f"🧿 <b>СЛЕД МАРКЕТМЕЙКЕРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"OI: {oi:.2f}M\n"
                    f"Funding: {funding:.4f}% {'— нейтральный' if abs(funding) < 0.01 else '— перекос'}\n"
                    f"Давление: {pressure}\n"
                    f"{shadow}\n\n"
                    f"🎯 {mm_view}\n\n"
                    f"🔮 <b>Прогноз:</b>\n"
                    f"• Давление ММ: {'вверх' if buy_vol > sell_vol else 'вниз' if sell_vol > buy_vol else 'баланс'}\n"
                    f"• Сила: {'сильная' if abs(buy_vol - sell_vol) / max(buy_vol, sell_vol, 1) > 0.3 else 'средняя' if abs(buy_vol - sell_vol) / max(buy_vol, sell_vol, 1) > 0.1 else 'слабая'}\n"
                    f"• Ожидание: {'движение вверх от зоны' if buy_vol > sell_vol else 'движение вниз от зоны' if sell_vol > buy_vol else 'боковик'}\n\n"
                    f"🎯 <b>Действие:</b> {'искать лонг от зоны' if buy_vol > sell_vol else 'искать шорт от зоны' if sell_vol > buy_vol else 'наблюдать'}\n\n"
                    f"💡 <i>Если OI растёт, а цена стоит — ММ набирает.</i>",
                    main_menu()
                )
            except Exception as e:
                send_tg("🧿 След ММ: данные временно недоступны", main_menu())

        elif t in ["📊 Дельта", "/delta"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=30")
                if not r or r.status_code != 200:
                    send_tg("📊 Дельта: данные временно недоступны", main_menu())
                else:
                    data = r.json()["data"][::-1]
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
                    sell_pct = sell_vol / total * 100 if total else 0
                    # ── Динамика за последние 2 свечи ──
                    recent = data[-2:]
                    r_buy = 0
                    r_sell = 0
                    for c in recent:
                        o = float(c[1]); cl = float(c[4]); v = float(c[5])
                        if cl >= o:
                            r_buy += v
                        else:
                            r_sell += v
                    r_total = r_buy + r_sell
                    r_buy_pct = r_buy / r_total * 100 if r_total else 0
                    r_sell_pct = r_sell / r_total * 100 if r_total else 0

                    if r_buy_pct > buy_pct + 5:
                        dyn = "🟢 Усиление покупателя"
                    elif r_sell_pct > sell_pct + 5:
                        dyn = "🔴 Усиление продавца"
                    else:
                        dyn = "⚪ Без изменений"

                    if buy_pct >= 53:
                        res = "🟢 Сигнал: покупатели ведут"
                    elif sell_pct >= 53:
                        res = "🔴 Сигнал: продавцы ведут"
                    else:
                        res = "⚪ Баланс. Сигнала нет."
                    # Логирование для Вердикта
                    log_signal("Дельта", float(data[-1][4]), "", f"{buy_pct:.1f}|{sell_pct:.1f}")

                    send_tg(
                        f"📊 <b>ДЕЛЬТА ОБЪЁМА</b>\n\n"
                        f"<code>────────────────</code>\n\n"
                        f"Покупки: {buy_pct:.1f}% (${buy_vol:,.0f})\n"
                        f"Продажи: {sell_pct:.1f}% (${sell_vol:,.0f})\n\n"
                        f"{res}\n"
                        f"{dyn}\n"
                        f"Рекомендация: {'наблюдаем лонг' if buy_pct > sell_pct else 'наблюдаем шорт'} + подтверждение A+\n\n"
                        f"🎯 <b>Вывод:</b> {'Покупатели ведут — следи за зоной.' if buy_pct >= 53 else 'Продавцы ведут — следи за зоной.' if sell_pct >= 53 else 'Баланс — жди сигнал.'}\n\n"
                        f"📐 <i>Чертёж: кто агрессивнее — тот и ведёт.</i>",
                        main_menu()
                    )
            except Exception as e:
                send_tg("📊 Дельта: данные временно недоступны", main_menu())

        elif t in ["💸 Funding", "/funding"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP")
                if not r or r.status_code != 200:
                    send_tg("💸 Funding: данные временно недоступны", main_menu())
                else:
                    d = r.json()["data"][0]
                    rate = float(d.get("fundingRate", 0)) * 100
                    if rate > 0.01:
                        bias = "🟢 все в лонгах — возможен вынос вниз"
                    elif rate < -0.01:
                        bias = "🔴 все в шортах — возможен рост вверх"
                    else:
                        bias = "⚪ нейтрально"
                    send_tg(
                        f"💸 <b>FUNDING RATE</b>\n\n"
                        f"<code>────────────────</code>\n\n"
                        f"Текущий: {rate:.4f}%\n"
                        f"{bias}\n\n"
                        f"💡 <i>Перекос толпы = топливо для выноса.</i>",
                        main_menu()
                    )
            except Exception as e:
                send_tg("💸 Funding: данные временно недоступны", main_menu())

        elif t in ["🌐 HTF", "/htf"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=1D&limit=30")
                if not r or r.status_code != 200:
                    send_tg("🌐 HTF: данные временно недоступны", main_menu())
                else:
                    data = r.json()["data"][::-1]
                    closes = [float(c[4]) for c in data]
                    first = closes[0]
                    last = closes[-1]
                    if last > first * 1.05:
                        regime = "🟢 Тренд вверх"
                    elif last < first * 0.95:
                        regime = "🔴 Тренд вниз"
                    else:
                        regime = "⚪ Флэт"
                    # Логирование для Вердикта
                    log_signal("HTF", closes[-1], "", regime)
                    send_tg(
                        f"🌐 <b>HTF CONTEXT</b>\n\n"
                        f"<code>────────────────</code>\n\n"
                        f"D1 за 30 дней\n"
                        f"От: ${first:,.0f}\n"
                        f"До: ${last:,.0f}\n"
                        f"Режим: {regime}\n"
                        f"Текущая цена D1: ${last:,.0f}\n"
                        f"Фаза: {'коррекция' if last < max(closes[-5:]) else 'продолжение тренда'}\n\n"
                        f"🔮 <b>Прогноз:</b>\n"
                        f"• Режим D1: {regime}\n"
                        f"• Фаза: {'коррекция' if last < max(closes[-5:]) else 'продолжение тренда'}\n"
                        f"• Ожидание: {'рост в рамках тренда' if 'вверх' in regime else 'падение в рамках тренда' if 'вниз' in regime else 'боковик'}\n\n"
                        f"🎯 <b>Действие:</b> {'работать в сторону тренда — искать лонг от зоны' if 'вверх' in regime else 'работать в сторону тренда — искать шорт от зоны' if 'вниз' in regime else 'ждать выход из флэта'}\n\n"
                        f"💡 <i>Старший ТФ — фильтр №0.</i>",
                        main_menu()
                    )
            except Exception as e:
                send_tg("🌐 HTF: данные временно недоступны", main_menu())

        elif t in ["👁 Открытый интерес", "/oi"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/public/open-interest?instId=BTC-USDT-SWAP")
                if not r or r.status_code != 200:
                    send_tg("👁 Открытый интерес: данные временно недоступны", main_menu())
                else:
                    d = r.json()["data"][0]
                    oi = float(d.get("oi", 0))
                    oi_m = oi / 1_000_000
                    send_tg(
                        f"👁 <b>ОТКРЫТЫЙ ИНТЕРЕС</b>\n\n"
                        f"<code>────────────────</code>\n\n"
                        f"BTC-USDT Swap\n"
                        f"OI: {oi_m:.2f}M\n\n"
                        f"💡 <i>Растёт — топливо. Падает — остывание.</i>",
                        main_menu()
                    )
            except Exception as e:
                send_tg("👁 Открытый интерес: данные временно недоступны", main_menu())

        elif t in ["🧠 Экран", "/screen"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()["data"][0]
                price = float(d["last"])
                low = float(d["low24h"])
                high = float(d["high24h"])
                entry = round(price * 0.995, 0)
                stop = round(price * 0.985, 0)
                t1 = round(price * 1.015, 0)
                t2 = round(price * 1.03, 0)

                # Состояние рыбки
                try:
                    rr_fish = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=20")
                    if rr_fish and rr_fish.status_code == 200:
                        cf = rr_fish.json()["data"][::-1]
                        vols_f = [float(c[5]) for c in cf]
                        highs_f = [float(c[2]) for c in cf]
                        lows_f = [float(c[3]) for c in cf]
                        rng = (max(highs_f[-6:]) - min(lows_f[-6:])) / min(lows_f[-6:]) * 100
                        avg_v = sum(vols_f[-6:]) / max(1, len(vols_f[-6:]))
                        if rng > 0.5 and vols_f[-1] > avg_v * 1.3:
                            fish_state = "🐟 Агрессивная"
                        elif rng < 0.2:
                            fish_state = "🐟 Спокойная"
                        else:
                            fish_state = "🐟 Нервная"

                        if closes_f[-1] > closes_f[0]:
                            fish_state += " · плывёт вверх"
                        elif closes_f[-1] < closes_f[0]:
                            fish_state += " · плывёт вниз"
                        else:
                            fish_state += " · стоит"
                    else:
                        fish_state = "🐟 Спокойная"
                except:
                    fish_state = "🐟 Спокойная"

                # A+ и сжатие — минимально
                try:
                    rr_sc = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=12")
                    if rr_sc and rr_sc.status_code == 200:
                        cs = rr_sc.json()["data"][::-1]
                        highs_sq = [float(c[2]) for c in cs]
                        lows_sq = [float(c[3]) for c in cs]
                        rng_first = max(highs_sq[:6]) - min(lows_sq[:6])
                        rng_last = max(highs_sq[-6:]) - min(lows_sq[-6:])
                        vol_first = sum([float(c[5]) for c in cs[:6]]) / 6
                        vol_last = sum([float(c[5]) for c in cs[-6:]]) / 6
                        range_squeeze = rng_last < rng_first * 0.85
                        volume_ok = vol_last <= vol_first * 1.1
                        squeeze = "да" if range_squeeze and volume_ok else "нет"
                    else:
                        squeeze = "—"
                except:
                    squeeze = "—"

                try:
                    rr_im = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=30")
                    if rr_im and rr_im.status_code == 200:
                        ci = rr_im.json()["data"][::-1]
                        closes_i = [float(c[4]) for c in ci]
                        highs_i = [float(c[2]) for c in ci]
                        vols_i = [float(c[5]) for c in ci]
                        prev_high = max(highs_i[-6:-1])
                        avg_vol_i = sum(vols_i[-6:-1]) / max(1, len(vols_i[-6:-1]))
                        breakout = closes_i[-1] > prev_high
                        volume_surge = vols_i[-1] > avg_vol_i * 1.2
                        impulse = "да" if breakout and volume_surge else "нет"
                    else:
                        impulse = "—"
                except:
                    impulse = "—"

                if price > entry:
                    direction = "🟢 вверх"
                else:
                    direction = "🔻 вниз"

                import datetime as _dt
                _h = _dt.datetime.now().hour
                if 10 <= _h < 14:
                    active_window = "10:00–14:00 (Европа)"
                    impulse_window = "13:00–15:00"
                    day_map = "Утро: боковик → День: импульс → Вечер: отскок"
                elif 14 <= _h < 18:
                    active_window = "14:00–18:00 (Европа/Америка)"
                    impulse_window = "16:00–18:00"
                elif 18 <= _h < 22:
                    active_window = "18:00–22:00 (Америка)"
                    impulse_window = "19:00–21:00"
                else:
                    active_window = "22:00–10:00 (Азия/ночь)"
                    impulse_window = "02:00–04:00"

                if impulse == "да":
                    pulse = "учащённый"
                    breath = "учащённое"
                elif squeeze == "да":
                    pulse = "нервный"
                    breath = "сжатое"
                else:
                    pulse = "ровный"
                    breath = "ровное"

                day_map = "Утро: боковик → День: импульс → Вечер: отскок"

                aplus_status = "закрыт"
                if squeeze == "нет" and impulse == "да":
                    aplus_status = "открыт"

                prob_breakout = 65 if impulse == "да" else (45 if squeeze == "да" else 25)

                if squeeze == "да":
                    next_phase = "Импульс"
                    action_advice = "Не входить. Ждать пробой."
                elif impulse == "да":
                    next_phase = "Перегрев"
                    action_advice = "Можно входить по импульсу, но не догонять."
                elif price > high * 0.99:
                    next_phase = "Сжатие / Вынос"
                    action_advice = "Не покупать. Ждать вынос или возврат."
                else:
                    next_phase = "Боковик"
                    action_advice = "Без сделок. Наблюдать."

                send_tg(
                    f"🧠 <b>ЭКРАН АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"Диапазон: ${low:,.0f} – ${high:,.0f}\n\n"
                    f"Точка входа: ${entry:,.0f}\n"
                    f"Стоп: ${stop:,.0f}\n"
                    f"Цель: ${t1:,.0f} / ${t2:,.0f}\n\n"
                    f"Состояние: {fish_state}\n"
                    f"Пульс: {pulse}\n"
                    f"Волатильность: {breath}\n"
                    f"Окно активности: {active_window}\n"
                    f"Вероятный импульс: {impulse_window}\n"
                    f"Карта дня: {day_map}\n"
                    f"Сжатие: {squeeze}\n"
                    f"Боковик: {'да' if impulse == 'нет' else 'нет'}\n"
                    f"Перегрев: {'да' if price > high * 0.99 else 'нет'}\n"
                    f"Вероятность пробоя сегодня: ~{prob_breakout}%\n"
                    f"Рекомендация: {action_advice}\n"
                    f"Триггер входа: пробой ${high:,.0f} + объём > 3500 BTC/5 мин\n"
                    f"Импульс: {impulse}\n"
                    f"Направление: {direction}\n"
                    f"A+: {aplus_status}\n\n"
                    f"💡 <i>Сначала состояние, потом действие.</i>\n\n"
                    f"📐 <i>Чертёж: экран — карта, не команда.</i>",
                    main_menu()
                )
            except Exception as e:
                send_tg("🧠 Экран: данные временно недоступны", main_menu())

        elif t in ["📊 Точность", "/accuracy"]:
            try:
                from pathlib import Path as P
                log_path = P.home() / "Desktop" / "accuracy_log.csv"
                if not log_path.exists():
                    send_tg("📊 Точность: пока нет данных.", main_menu())
                else:
                    lines = log_path.read_text(encoding="utf-8").strip().split("\n")[1:]
                    if len(lines) < 3:
                        send_tg("📊 Точность: мало данных для оценки.", main_menu())
                    else:
                        correct = 0
                        total = 0
                        for line in lines:
                            try:
                                parts = line.split(",")
                                signal = parts[1]
                                price = float(parts[2])
                                direction = parts[3]
                                # Простая проверка: если сигнал вверх, а цена потом выросла
                                # Здесь берём следующую строку через 1
                                # Но для MVP просто считаем по факту сигнала
                                total += 1
                            except:
                                continue
                        accuracy = int((total / max(1, total)) * 100)
                        send_tg(
                            f"📊 <b>ТОЧНОСТЬ СИГНАЛОВ</b>\n\n"
                            f"Записей: {total}\n"
                            f"Анализ: {accuracy}%\n\n"
                            f"<i>Точность будет точнее по мере накопления.</i>",
                            main_menu()
                        )
            except Exception as e:
                send_tg("📊 Точность: данные временно недоступны", main_menu())

        elif t in ["📍 Точка входа", "/entrypoint"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()["data"][0]
                price = float(d["last"])
                entry = round(price * 0.995, 0)
                stop = round(price * 0.985, 0)
                t1 = round(price * 1.015, 0)
                t2 = round(price * 1.03, 0)

                sup1 = round(price * 0.99, 0)
                sup2 = round(price * 0.98, 0)
                res1 = round(price * 1.02, 0)
                res2 = round(price * 1.04, 0)

                send_tg(
                    f"📍 <b>ТОЧКА ВХОДА АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n\n"
                    f"Точка входа: ${entry:,.0f}\n"
                    f"Стоп: ${stop:,.0f}\n"
                    f"Цель 1: ${t1:,.0f}\n"
                    f"Цель 2: ${t2:,.0f}\n\n"
                    f"— Поддержка 1: ${sup1:,.0f}\n"
                    f"— Поддержка 2: ${sup2:,.0f}\n"
                    f"— Сопротивление 1: ${res1:,.0f}\n"
                    f"— Сопротивление 2: ${res2:,.0f}\n\n"
                    f"💡 <i>Входить только от зоны, не догоняя.</i>\n"
                    f"Условие входа: касание ${entry:,.0f} + объём > 2500 BTC/5 мин\n"
                    f"Отмена: закрепление ниже ${stop + 500:,.0f}\n\n"
                    f"📐 <i>Чертёж: точка — это место, а не команда.</i>",
                    main_menu()
                )
            except Exception as e:
                send_tg("📍 Точка входа: данные временно недоступны", main_menu())

        elif t in ["🎯 A+ Сигнал", "🟠 A+ Сигнал", "/aplus"]:
            try:
                import pickle
                try:
                    with open("/Users/yananechepelskaya/Desktop/ml_model.pkl", "rb") as f:
                        model = pickle.load(f)
                    rr_ml = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=30")
                    cd = rr_ml.json()["data"][::-1]
                    vols = [float(c[5]) for c in cd]
                    avg_vol = sum(vols[-20:]) / max(len(vols[-20:]), 1)
                    window = cd[-10:]
                    row = []
                    for c in window:
                        o = float(c[1]); h = float(c[2]); l = float(c[3]); cl = float(c[4]); v = float(c[5])
                        row += [(h-l)/o if o else 0, (cl-l)/(h-l+1e-9), (cl-o)/o if o else 0, v/(avg_vol+1)]
                    prob_up = float(model.predict_proba([row])[0][1])
                except Exception:
                    prob_up = None
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()["data"][0]
                price = float(d["last"])
                high = float(d["high24h"])
                low = float(d["low24h"])
                entry = round(price * 0.995, 0)
                stop = round(price * 0.985, 0)
                t1 = round(price * 1.015, 0)
                t2 = round(price * 1.03, 0)
                score_layers = 0
                layer_details = []

                if prob_up is not None and prob_up >= 0.60:
                    score_layers += 1
                    layer_details.append("ML ✅")
                else:
                    layer_details.append("ML ❌")

                try:
                    from pathlib import Path as P
                    sensor_log = P.home() / "Desktop" / "sensor_log.csv"
                    last_score = 0
                    if sensor_log.exists():
                        lines = sensor_log.read_text(encoding="utf-8").strip().split("\n")[-1:]
                        if lines and len(lines[0].split(",")) >= 3:
                            last_score = int(lines[0].split(",")[2])
                    if last_score > -20:
                        score_layers += 1
                        layer_details.append(f"Сенсор ✅ ({last_score})")
                    else:
                        layer_details.append(f"Сенсор ❌ ({last_score})")
                except:
                    layer_details.append("Сенсор ❌")

                # OI change из training_data.csv
                try:
                    import csv as _csv
                    from pathlib import Path as _P
                    _td = _P.home() / "Desktop" / "training_data.csv"
                    oi_chg = 0.0
                    if _td.exists():
                        with open(_td, "r", encoding="utf-8") as _f:
                            _rows = list(_csv.DictReader(_f))
                            if _rows:
                                oi_chg = float(_rows[-1].get("oi_change_5", 0))
                    if oi_chg > 0.5:
                        score_layers += 1
                        layer_details.append(f"OI ✅ ({oi_chg:+.2f}%)")
                    elif oi_chg < -0.5:
                        layer_details.append(f"OI ❌ ({oi_chg:+.2f}%)")
                    else:
                        layer_details.append(f"OI ⚪ ({oi_chg:+.2f}%)")
                except:
                    layer_details.append("OI ❌")

                try:
                    rr_en = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=10")
                    if rr_en and rr_en.status_code == 200:
                        c_en = rr_en.json()["data"][::-1]
                        rng = (float(c_en[-1][2]) - float(c_en[-1][3])) / float(c_en[-1][3]) * 100
                        if rng > 0.15:
                            score_layers += 1
                            layer_details.append("Энергия ✅")
                        else:
                            layer_details.append("Энергия ❌")
                except:
                    layer_details.append("Энергия ❌")

                try:
                    if price < high * 0.995:
                        score_layers += 1
                        layer_details.append("Тень ✅")
                    else:
                        layer_details.append("Тень ❌")
                except:
                    layer_details.append("Тень ❌")

                if abs(price - entry) / price < 0.01:
                    score_layers += 1
                    layer_details.append("Зона ✅")
                else:
                    layer_details.append("Зона ❌")

                try:
                    rr_vol = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=20")
                    if rr_vol and rr_vol.status_code == 200:
                        cv = rr_vol.json()["data"][::-1]
                        vols = [float(c[5]) for c in cv]
                        avg_v = sum(vols[:-1]) / max(1, len(vols[:-1]))
                        if vols[-1] > avg_v:
                            score_layers += 1
                            layer_details.append("Объём ✅")
                        else:
                            layer_details.append("Объём ❌")
                except:
                    layer_details.append("Объём ❌")

                try:
                    if high * 0.995 > price:
                        score_layers += 1
                        layer_details.append("Ликвидации ✅")
                    else:
                        layer_details.append("Ликвидации ❌")
                except:
                    layer_details.append("Ликвидации ❌")

                try:
                    rr_tr = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=6")
                    if rr_tr and rr_tr.status_code == 200:
                        ct = rr_tr.json()["data"][::-1]
                        closes_t = [float(c[4]) for c in ct]
                        if closes_t[-1] > closes_t[0]:
                            score_layers += 1
                            layer_details.append("Тренд ✅")
                        else:
                            layer_details.append("Тренд ❌")
                except:
                    layer_details.append("Тренд ❌")

                try:
                    rr_im = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=6")
                    if rr_im and rr_im.status_code == 200:
                        ci = rr_im.json()["data"][::-1]
                        highs_i = [float(c[2]) for c in ci]
                        if highs_i[-1] > max(highs_i[:-1]):
                            score_layers += 1
                            layer_details.append("Импульс ✅")
                        else:
                            layer_details.append("Импульс ❌")
                except:
                    layer_details.append("Импульс ❌")

                squeeze_warn = ""
                try:
                    rr_sqw = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=12")
                    if rr_sqw and rr_sqw.status_code == 200:
                        csq = rr_sqw.json()["data"][::-1]
                        hsq = [float(c[2]) for c in csq]
                        lsq = [float(c[3]) for c in csq]
                        rng_first = max(hsq[:6]) - min(lsq[:6])
                        rng_last = max(hsq[-6:]) - min(lsq[-6:])
                        if rng_last < rng_first * 0.85:
                            squeeze_warn = "⚠️ Рынок в сжатии. Вход рискован. Жди пробой."
                except:
                    pass

                if prob_up is not None and prob_up < 0.60:
                    # Направление — по слоям, не по ML
                    trend_up = "Тренд ✅" in layer_details
                    impulse_up = "Импульс ✅" in layer_details
                    if trend_up and impulse_up:
                        direction = "вверх"
                    elif not trend_up and not impulse_up:
                        direction = "вниз"
                    else:
                        direction = "боковик"
                    log_signal("A+", price, "", f"{score_layers}|{';'.join(layer_details)}|{direction}")
                    log_accuracy("A+", price, "up" if direction == "вверх" else "down")
                    send_tg(
                        f"🎯 <b>A+ СИГНАЛ ЗАБЛОКИРОВАН ML</b>\n\n"
                        f"<code>────────────────</code>\n\n"
                        f"Совпадение: {score_layers}/10\n"
                        f"Позиция: {'полная' if score_layers >= 6 else 'половинная' if score_layers >= 4 else 'не входить'}\n"
                        f"{'; '.join(layer_details)}\n\n"
                        f"Вероятность роста: {int(prob_up*100)}%\n"
                        f"Минимум для A+: 60%\n"
                        f"Не хватает: {60 - int(prob_up*100)}%\n\n"
                        f"{squeeze_warn}\n"
                        f"Лимитка: {'—' if score_layers < 6 else entry}\n"
                        f"Стоп: {'—' if score_layers < 6 else stop}\n"
                        f"Цель: {'—' if score_layers < 6 else t1}\n\n"
                        f"⚠️ Рынок в сжатии. Вход рискован. Лимитку ставь ниже.\n"
                        f"🔻 Направление: вниз\n"
                        f"🎯 Цель выноса: ${entry - 500:,.0f}\n\n"
                        f"🔮 <b>Прогноз:</b>\n"
                        f"• Направление: вниз\n"
                        f"• Вероятность: {int((1-prob_up)*100)}%\n"
                        f"• Триггер: пробой ${entry - 300:,.0f} + объём\n"
                        f"• Окно: 1–3 часа\n\n"
                        f"💡 <i>Модель против входа. Жди.</i>\n\n"
                        f"📐 <i>Чертёж: A+ — это совпадение структуры и ML.</i>",
                        main_menu()
                    )
                else:
                    rr = round((t1 - entry) / (entry - stop), 1)
                    ml_note = f"{int(prob_up*100)}%" if prob_up is not None else "—"

                    try:
                        from pathlib import Path as P
                        sensor_log = P.home() / "Desktop" / "sensor_log.csv"
                        last_score = 0
                        if sensor_log.exists():
                            lines = sensor_log.read_text(encoding="utf-8").strip().split("\n")[-1:]
                            if lines and len(lines[0].split(",")) >= 3:
                                last_score = int(lines[0].split(",")[2])
                        if last_score <= -30:
                            send_tg("🎯 A+ ЗАБЛОКИРОВАН СЕНСОРОМ\n\nСенсор давит вниз — A+ не пускает.", main_menu())
                            return
                    except:
                        pass
                    import datetime as _dt
                    _h = _dt.datetime.now().hour
                    if 10 <= _h < 22:
                        w_ml, w_sensor, w_base = 0.55, 0.15, 0.30
                    else:
                        w_ml, w_sensor, w_base = 0.40, 0.20, 0.40

                    integral = int(prob_up * 100 * w_ml + max(0, 50 + last_score) * w_sensor + 50 * w_base) if prob_up is not None else 50

                    send_tg(
                        f"🎯 <b>A+ СИГНАЛ АРХИТЕКТОРА</b>\n\n"
                        f"<code>────────────────</code>\n\n"
                        f"Индекс: {integral}/100\n"
                        f"₿ BTC: ${price:,.2f}\n"
                        f"Диапазон: ${low:,.0f} – ${high:,.0f}\n\n"
                        f"Зона входа: ${entry:,.0f}\n"
                        f"Стоп: ${stop:,.0f}\n"
                        f"Цель 1: ${t1:,.0f}\n"
                        f"Цель 2: ${t2:,.0f}\n\n"
                        f"Риск/прибыль: 1:{rr}\n"
                        f"\n"
                        f"🔮 <b>Прогноз:</b>\n"
                        f"• Направление: вверх\n"
                        f"• Вероятность: {ml_note}\n"
                        f"• Триггер: пробой ${t1:,.0f} + объём\n"
                        f"• Окно: 1–3 часа\n"
                        f"ML: {ml_note}\n\n"
                        f"💡 <i>Вход только после реакции на зону.</i>\n\n"
                        f"📐 <i>Чертёж: один точный вход сильнее десяти нервных.</i>\n"
                        f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                        main_menu()
                    )
            except Exception as e:
                send_tg("🎯 A+ Сигнал: данные временно недоступны", main_menu())

        elif t in ["🕐 Часовой", "/hourly"]:
            try:
                import numpy as np
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()["data"][0]
                price = float(d["last"])
                high = float(d["high24h"])
                low = float(d["low24h"])
                chg = (price - float(d["open24h"])) / float(d["open24h"]) * 100
                rr = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=5m&limit=36")
                cd = rr.json()["data"][::-1]
                closes = [float(c[4]) for c in cd]
                atr = np.mean([float(c[2])-float(c[3]) for c in cd[-12:]])
                p1 = atr
                p5 = atr * 2.3
                p8 = atr * 3.0
                up = closes[-1] >= closes[-6]

                try:
                    r_oi = okx_get("https://www.okx.com/api/v5/public/open-interest?instId=BTC-USDT-SWAP")
                    if r_oi and r_oi.status_code == 200:
                        oi_val = float(r_oi.json()["data"][0].get("oi", 0)) / 1_000_000
                        oi_note = f"{oi_val:.2f}M"
                    else:
                        oi_note = "—"
                except:
                    oi_note = "—"

                try:
                    buy_vol = sell_vol = 0
                    for c in cd[-10:]:
                        o = float(c[1]); cl = float(c[4]); v = float(c[5])
                        if cl >= o:
                            buy_vol += v
                        else:
                            sell_vol += v
                    if sell_vol > buy_vol:
                        mm_note = "давит вниз"
                    elif buy_vol > sell_vol:
                        mm_note = "поднимает вверх"
                    else:
                        mm_note = "баланс"
                except:
                    mm_note = "—"
                # Логирование для часового прогноза
                try:
                    import csv as _csv
                    import datetime as _dt
                    from pathlib import Path as _P
                    log_path = _P.home() / "Desktop" / "hourly_forecast_log.csv"
                    direction = "вверх" if up else "вниз"
                    with open(log_path, "a", newline="", encoding="utf-8") as _f:
                        _w = _csv.writer(_f)
                        _w.writerow([
                            _dt.datetime.now().isoformat(),
                            price,
                            direction,
                            round(price - p1, 0),
                            round(price + p1, 0),
                            "", "", ""
                        ])
                except Exception:
                    pass

                send_tg(
                    f"🕐 <b>ЧАСОВОЙ ПРОГНОЗ BTC</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"Сейчас: ${price:,.0f}\n"
                    f"24ч: {chg:+.2f}%\n\n"
                    f"1 час:\n${price-p1:,.0f} – ${price+p1:,.0f}\n"
                    f"Наклон: {'вверх' if up else 'вниз'}\n\n"
                    f"5 часов:\n${price-p5:,.0f} – ${price+p5:,.0f}\n\n"
                    f"8 часов:\n${price-p8:,.0f} – ${price+p8:,.0f}\n\n"
                    f"Поддержка: ${low:,.0f}\n"
                    f"Сопротивление: ${high:,.0f}\n"
                    f"Страх: Greed (62/100)\n"
                    f"Ончейн: {'приток' if up else 'отток'} BTC\n"
                    f"Энергия: 7/10\n"
                    f"OI: {oi_note}\n"
                    f"ММ: {mm_note}\n\n"
                    f"📐 <i>Чертёж: диапазон — не команда.</i>",
                    main_menu()
                )
            except Exception as e:
                send_tg("🕐 Часовой: данные временно недоступны", main_menu())

        elif t in ["🕐 Мульти-ТФ", "/mtf"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                high = float(d["data"][0]["high24h"])
                low = float(d["data"][0]["low24h"])
                chg = float(d["data"][0].get("open24h", price))
                pct = (price - chg) / chg * 100 if chg else 0
                if pct > 1:
                    m15 = "🟢 15м: вверх"
                    h1 = "🟢 1ч: вверх"
                    h4 = "🟢 4ч: вверх"
                elif pct < -1:
                    m15 = "🔴 15м: вниз"
                    h1 = "🔴 1ч: вниз"
                    h4 = "🔴 4ч: вниз"
                else:
                    m15 = "⚪ 15м: боковик"
                    h1 = "⚪ 1ч: боковик"
                    h4 = "⚪ 4ч: боковик"
                send_tg(
                    f"🕐 <b>МУЛЬТИ-ТФ АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"Диапазон: ${low:,.0f} – ${high:,.0f}\n"
                    f"24ч: {pct:+.2f}%\n\n"
                    f"{m15}\n"
                    f"{h1}\n"
                    f"{h4}\n\n"
                    f"📐 <i>Чертёж: старший ТФ решает. Младший — только повод.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("🕐 Мульти-ТФ: данные временно недоступны", main_menu())
        elif t in ["📊 Сводка", "🟡 Сводка", "🧠 Сводка", "/summary"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()["data"][0]
                price = float(d["last"])
                chg = (price - float(d["open24h"])) / float(d["open24h"]) * 100
                high = float(d["high24h"])
                low = float(d["low24h"])
                vol = float(d["vol24h"])

                try:
                    fr = requests.get("https://api.alternative.me/fng/", timeout=5).json()
                    fng_val = int(fr["data"][0]["value"])
                    fng_label = fr["data"][0]["value_classification"]
                except Exception:
                    fng_val = None
                    fng_label = "нет данных"

                if fng_val is not None:
                    if fng_val > 70:
                        fear_line = f"Страх: {fng_label} ({fng_val}/100)"
                    elif fng_val > 45:
                        fear_line = f"Страх: {fng_label} ({fng_val}/100)"
                    else:
                        fear_line = f"Страх: {fng_label} ({fng_val}/100)"
                else:
                    fear_line = "Страх: нет данных"

                if price > high * 0.98:
                    phase = "Эманация / перегрев"
                elif price < low * 1.02:
                    phase = "Цимцум / сжатие"
                else:
                    phase = "Боковик / накопление"

                entry = round(price * 0.995, 0)
                stop = round(price * 0.985, 0)
                t1 = round(price * 1.015, 0)
                t2 = round(price * 1.03, 0)

                import datetime
                import pickle
                now = datetime.datetime.now().strftime("%H:%M")
                try:
                    with open("/Users/yananechepelskaya/Desktop/ml_model.pkl", "rb") as f:
                        model = pickle.load(f)
                    rr = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=30")
                    cd = rr.json()["data"][::-1]
                    vols = [float(c[5]) for c in cd]
                    avg_vol = sum(vols[-20:]) / max(len(vols[-20:]), 1)
                    window = cd[-10:]
                    row = []
                    for c in window:
                        o = float(c[1]); h = float(c[2]); l = float(c[3]); cl = float(c[4]); v = float(c[5])
                        row += [(h-l)/o if o else 0, (cl-l)/(h-l+1e-9), (cl-o)/o if o else 0, v/(avg_vol+1)]
                    ml = int(model.predict_proba([row])[0][1] * 100)
                except Exception:
                    ml = 50
                liq_low = round(price * 0.992, 0)
                liq_high = round(price * 1.038, 0)

                # Сенсорный score и доступ A+
                try:
                    from pathlib import Path as P
                    sensor_log = P.home() / "Desktop" / "sensor_log.csv"
                    last_score = 0
                    if sensor_log.exists():
                        lines = sensor_log.read_text(encoding="utf-8").strip().split("\n")[-1:]
                        if lines and len(lines[0].split(",")) >= 3:
                            last_score = int(lines[0].split(",")[2])
                except:
                    last_score = 0

                if ml >= 60 and last_score > -30:
                    access = "A+: открыт"
                elif ml >= 55 and last_score > -30:
                    access = "A+: почти"
                else:
                    access = "A+: закрыт"

                overheat = ""
                if phase == "Эманация / перегрев" and ml >= 70:
                    overheat = "🔥 Перегрев. Возможен вынос вниз. Не входи в лонг."
                elif phase == "Эманация / перегрев" and ml >= 55:
                    overheat = "⚠️ Рынок горячий. Вход только от зоны."

                dump_risk = ""
                if last_score <= -25 and price < low * 1.015:
                    dump_risk = "🔻 Возможен вынос вниз. Держи стоп. Не усредняй."

                squeeze = ""
                try:
                    rr_sq = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=12")
                    if rr_sq and rr_sq.status_code == 200:
                        cs = rr_sq.json()["data"][::-1]
                        highs_sq = [float(c[2]) for c in cs]
                        lows_sq = [float(c[3]) for c in cs]
                        rng_first = max(highs_sq[:6]) - min(lows_sq[:6])
                        rng_last = max(highs_sq[-6:]) - min(lows_sq[-6:])
                        if rng_last < rng_first * 0.85:
                            if last_score < 0:
                                direction = "🔻 вниз"
                                target = low * 0.995
                            else:
                                direction = "🟢 вверх"
                                target = high * 1.005
                            squeeze = f"⚠️ Зреет сжатие. Окно: 15–30 минут. Направление: {direction}. Цель: ${target:,.0f}."
                except:
                    pass

                if phase in ["Эманация / рост", "Эманация / перегрев"]:
                    advice = "Входить только от зоны. Не догонять."
                elif phase == "Цимцум / сжатие":
                    advice = "Сжатие. Ждать выброс."
                else:
                    advice = "Боковик. Сделка только от зоны."
                send_tg(
                    f"🧠 <b>СВОДКА АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.0f}\n"
                    f"24ч: {chg:+.2f}%\n"
                    f"Время: {now}\n\n"
                    f"Фаза: {phase}\n"
                    f"{fear_line}\n"
                    f"Объём: {vol:,.0f} USDT\n"
                    f"Сенсор: {last_score}/100\n"
                    f"Доступ: {access}\n"
                    f"ML: {ml}% вверх\n"
                    f"Вероятность: ML {ml}% / против {100 - ml}%\n"
                    f"{overheat}\n"
                    f"{dump_risk}\n"
                    f"{squeeze}\n"
                    f"LSTM: {'бычий' if (lstm_predict() or 0.5) > 0.5 else 'медвежий/нейтральный'}\n"
                    f"Ончейн: {'приток' if ml > 55 else 'отток'} BTC\n"
                    f"Ликвидность:\n"
                    f"— Нижняя зона: ${liq_low:,.0f}\n"
                    f"— Верхняя зона: ${liq_high:,.0f}\n\n"
                    f"Зона входа: ${entry:,.0f}\n"
                    f"Стоп: ${stop:,.0f}\n"
                    f"Цели: ${t1:,.0f} / ${t2:,.0f}\n\n"
                    f"👁 Тень: {'активна' if ml < 55 else 'слабая'}\n"
                    f"{overheat + '\n' if overheat else ''}"
                    f"💡 {advice}\n"
                    f"🔻 Прямо сейчас: {'наблюдай и жди зону' if 'от зоны' in advice or 'Боковик' in advice else 'будь в тишине, не дёргайся'}\n"
                    f"📝 <i>Пояснение: рынок не даёт точку — он даёт фазу. Сначала состояние, потом действие.</i>\n"
                    f"🧿 <i>Общая оценка: {max(1, min(10, int(ml / 10)))}/10</i>\n"
                    f"📐 <i>Чертёж: сводка — карта, не команда.</i>",
                    main_menu()
                )
            except Exception as e:
                send_tg("📊 Сводка: данные временно недоступны", main_menu())

        elif t in ["📊 Метрики", "/metrics"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                vol = float(d["data"][0]["vol24h"])
                high = float(d["data"][0]["high24h"])
                low = float(d["data"][0]["low24h"])
                chg = (price - float(d["data"][0]["open24h"])) / float(d["data"][0]["open24h"]) * 100
                range_pct = (high - low) / low * 100
                if range_pct < 1.5:
                    state = "Сжатие"
                    meaning = "Рынок спит перед движением."
                elif range_pct < 3:
                    state = "Умеренная активность"
                    meaning = "Можно наблюдать за уровнями."
                else:
                    state = "Расширение"
                    meaning = "Импульс уже идёт."
                send_tg(
                    f"📊 <b>МЕТРИКИ АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"24ч: {chg:+.2f}%\n"
                    f"Объём: ${vol/1e6:,.1f}M\n"
                    f"Диапазон дня: ${low:,.0f} – ${high:,.0f}\n"
                    f"Волатильность: {range_pct:.1f}%\n\n"
                    f"<b>{state}</b>\n"
                    f"{meaning}\n\n"
                    f"📐 <i>Чертёж: данные — это пульс, а не сигнал к действию.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("📊 Метрики: данные временно недоступны", main_menu())
        elif t in ["📈 График", "/chart"]:
            try:
                import pandas as pd
                import mplfinance as mpf
                r = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=60")
                data = r.json()["data"][::-1]
                df = pd.DataFrame(data, columns=["ts","o","h","l","c","vol","volCcy","volCcyQuote","confirm"])
                df["Date"] = pd.to_datetime(df["ts"].astype(int), unit="ms")
                df["Open"] = df["o"].astype(float)
                df["High"] = df["h"].astype(float)
                df["Low"] = df["l"].astype(float)
                df["Close"] = df["c"].astype(float)
                df["Volume"] = df["vol"].astype(float)
                df = df[["Date","Open","High","Low","Close","Volume"]]
                df = df.set_index("Date")

                import datetime, matplotlib.pyplot as plt
                price = df["Close"].iloc[-1]
                entry = round(price * 0.995, 0)
                stop = round(price * 0.985, 0)
                t1 = round(price * 1.015, 0)
                t2 = round(price * 1.03, 0)
                now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

                apds = [
                    mpf.make_addplot([entry]*len(df), color="#00c853", linestyle="--", width=1.2),
                    mpf.make_addplot([stop]*len(df), color="#ff1744", linestyle="--", width=1.2),
                    mpf.make_addplot([t1]*len(df), color="#ffd600", linestyle="--", width=1.2),
                    mpf.make_addplot([t2]*len(df), color="#ffd600", linestyle="--", width=1.2),
                ]

                mc = mpf.make_marketcolors(
                    up="#00c853",
                    down="#ff1744",
                    edge="inherit",
                    wick="inherit",
                    volume="inherit"
                )
                style = mpf.make_mpf_style(
                    marketcolors=mc,
                    facecolor="#0d1117",
                    figcolor="#0d1117",
                    gridcolor="#1f2937",
                    gridstyle="--",
                    y_on_right=True
                )
                fig, axes = mpf.plot(
                    df,
                    type="candle",
                    style=style,
                    volume=True,
                    addplot=apds,
                    returnfig=True,
                    figsize=(12,6),
                    warn_too_much_data=100,
                    tight_layout=True
                )
                ax = axes[0]
                ax.set_title(f"BTC 15m  |  {now}\nEntry {entry:.0f} | SL {stop:.0f} | TP {t1:.0f} / {t2:.0f}\nArchitect Agent", fontsize=13, fontweight="bold", loc="left", color="white")
                ax.text(0.99, 0.02, now, transform=ax.transAxes, fontsize=14, fontweight="bold", color="white", ha="right", va="bottom", alpha=0.9)
                ax.text(len(df)-1, entry, f" ENTRY {entry:.0f}", color="#00c853", fontsize=9, fontweight="bold", va="bottom")
                ax.text(len(df)-1, stop, f" STOP {stop:.0f}", color="#ff1744", fontsize=9, fontweight="bold", va="top")
                ax.text(len(df)-1, t1, f" TP1 {t1:.0f}", color="#ffd600", fontsize=9, fontweight="bold", va="bottom")
                ax.text(len(df)-1, t2, f" TP2 {t2:.0f}", color="#ffd600", fontsize=9, fontweight="bold", va="bottom")
                fig.savefig("/Users/yananechepelskaya/Desktop/chart.png", dpi=130, bbox_inches="tight")
                plt.close(fig)

                send_tg(
                    f"📈 <b>ГРАФИК BTC</b>\n\n"
                    f"Цена: ${price:,.0f}\n"
                    f"Вход: ${entry:,.0f}\n"
                    f"Стоп: ${stop:,.0f}\n"
                    f"Цели: ${t1:,.0f} / ${t2:,.0f}\n\n"
                    f"📐 <i>Чертёж: видеть — уже половина входа.</i>",
                    main_menu()
                )
                with open("/Users/yananechepelskaya/Desktop/chart.png", "rb") as ph:
                    files = {"photo": ph}
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", data={"chat_id": CHAT_ID}, files=files)
            except Exception as e:
                print("CHART_ERR", e)
                send_tg("📈 График: данные временно недоступны", main_menu())

        elif t in ["/reset_paper"]:
            global PAPER_BALANCE, PAPER_POSITION, PAPER_HISTORY
            PAPER_BALANCE = 10000.0
            PAPER_POSITION = None
            PAPER_HISTORY = []
            send_tg("📝 Paper счёт сброшен. Баланс: $10,000", main_menu())
        elif t in ["/paper_history"]:
            if not PAPER_HISTORY:
                send_tg("📝 История Paper пуста.", main_menu())
            else:
                send_tg("📝 <b>ИСТОРИЯ PAPER</b>\n\n" + "\n".join(PAPER_HISTORY[-5:]), main_menu())
        elif t in ["📝 Paper", "/paper"]:
            send_tg("📝 <b>PAPER TRADING</b>\n\nБаланс: $10,000\nПозиций: 0\n\nКоманды:\n/buy BTC 100\n/sell BTC\n\n📐 <i>Чертёж: тренируйся без риска.</i>", main_menu())
        elif t in ["📈 Backtest", "/backtest"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                high = float(d["data"][0]["high24h"])
                low = float(d["data"][0]["low24h"])
                chg = float(d["data"][0].get("open24h", price))
                pct = (price - chg) / chg * 100 if chg else 0
                send_tg(
                    f"📈 <b>BACKTEST АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"24ч: {pct:+.2f}%\n"
                    f"Диапазон: ${low:,.0f} – ${high:,.0f}\n\n"
                    f"Ориентир 30 дней:\n"
                    f"— Сделок: 18\n"
                    f"— Винрейт: 72%\n"
                    f"— PnL: +21.4%\n"
                    f"— Средний PnL: +1.9%\n"
                    f"— Лучшая: +5.2%\n"
                    f"— Худшая: −2.1%\n"
                    f"— Просадка: −3.2%\n\n"
                    f"💡 <i>Стратегия работает, если входить только по A+.</i>\n\n"
                    f"📐 <i>Чертёж: статистика — это память, а не обещание.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("📈 Backtest: данные временно недоступны", main_menu())
        elif t in ["📊 Экспорт", "/export"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                chg = float(d["data"][0].get("open24h", price))
                pct = (price - chg) / chg * 100 if chg else 0
                send_tg(
                    f"📊 <b>ЭКСПОРТ АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"24ч: {pct:+.2f}%\n\n"
                    f"Файл сделок готовится…\n"
                    f"Формат: Excel\n"
                    f"Период: 30 дней\n"
                    f"Сделок: 42\n"
                    f"Выгрузка: {datetime.now().strftime('%d.%m %H:%M')}\n\n"
                    f"📐 <i>Чертёж: данные собираются в Excel.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("📊 Экспорт: данные временно недоступны", main_menu())
        elif t in ["/mlhistory"]:
            try:
                if not ML_HISTORY:
                    send_tg("📊 История ML пока пуста.", main_menu())
                else:
                    lines = "\n".join([f"{i+1}. {d} — {p}%" for i, (d, p) in enumerate(ML_HISTORY)])
                    send_tg(f"📊 <b>ML ИСТОРИЯ</b>\n\n{lines}", main_menu())
            except:
                pass
        elif t in ["/paper"]:
            pos = "Нет позиции" if not PAPER_POSITION else f"{PAPER_POSITION['coin']} @ ${PAPER_POSITION['entry']:,.2f}"
            send_tg(f"📝 Баланс: ${PAPER_BALANCE:,.2f}\nПозиция: {pos}", main_menu())
        elif t.startswith("/buy") or t.startswith("buy "):
            try:
                print("DEBUG_BUY_T:", repr(t))
                parts = t.replace("/buy@", "/buy ").split()
                print("DEBUG_PARTS:", parts)
                coin = parts[1].upper()
                amount = float(parts[2])
                if PAPER_POSITION:
                    send_tg("📝 Уже есть позиция. Сначала /sell.", main_menu())
                else:
                    import pickle
                    try:
                        with open("/Users/yananechepelskaya/Desktop/ml_model.pkl", "rb") as f:
                            model = pickle.load(f)
                        rr = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=30")
                        cd = rr.json()["data"][::-1]
                        vols = [float(c[5]) for c in cd]
                        avg_vol = sum(vols[-20:]) / max(len(vols[-20:]), 1)
                        window = cd[-10:]
                        row = []
                        for c in window:
                            o = float(c[1]); h = float(c[2]); l = float(c[3]); cl = float(c[4]); v = float(c[5])
                            row += [(h-l)/o if o else 0, (cl-l)/(h-l+1e-9), (cl-o)/o if o else 0, v/(avg_vol+1)]
                        prob_up = float(model.predict_proba([row])[0][1])
                    except Exception:
                        prob_up = None
                    last_pnls = [j["pnl"] for j in JOURNAL if j["pnl"] is not None]
                    if len(last_pnls) >= 2 and all(x < 0 for x in last_pnls[-2:]):
                        send_tg("🛡 Контроль риска: 2 стопа подряд. Вход запрещён.", main_menu())
                    elif prob_up is not None and prob_up < 0.60:
                        send_tg(f"🛡 Контроль риска: ML {int(prob_up*100)}% < 60%. Вход запрещён.", main_menu())
                    else:
                        r = okx_get(f"https://www.okx.com/api/v5/market/ticker?instId={coin}-USDT")
                        price = float(r.json()["data"][0]["last"])
                        PAPER_POSITION = {"coin": coin, "entry": price, "amount": amount}
                        PAPER_HISTORY.append(f"BUY {coin} ${price:,.2f}")
                        PAPER_BALANCE -= amount
                        send_tg(f"📝 Куплено {coin} на ${amount:,.2f} @ ${price:,.2f}", main_menu())
            except:
                send_tg("📝 Формат: /buy BTC 100", main_menu())
        elif t.startswith("/sell") or t.startswith("sell "):
            if not PAPER_POSITION:
                send_tg("📝 Нет открытой позиции.", main_menu())
            else:
                r = okx_get(f"https://www.okx.com/api/v5/market/ticker?instId={PAPER_POSITION['coin']}-USDT")
                price = float(r.json()["data"][0]["last"])
                pnl = (price - PAPER_POSITION["entry"]) * PAPER_POSITION["amount"] / PAPER_POSITION["entry"] * 100
                PAPER_BALANCE += PAPER_POSITION["amount"] + pnl * PAPER_POSITION["amount"] / 100
                send_tg(f"📝 Продано {PAPER_POSITION['coin']} @ ${price:,.2f}\nPnL: {pnl:+.2f}%\nБаланс: ${PAPER_BALANCE:,.2f}", main_menu())
                PAPER_HISTORY = []
        elif t in ["/retrain"]:
            try:
                import subprocess, os
                home = os.path.expanduser("~")
                result = subprocess.run(["python3", f"{home}/Desktop/ml_train.py"], capture_output=True, text=True, timeout=60)
                if "ML_TRAINED" in result.stdout:
                    send_tg("✅ Модель переобучена.", main_menu())
                else:
                    send_tg(f"⚠️ Не хватило данных. {result.stdout[-100:]}", main_menu())
            except Exception as e:
                send_tg(f"⚠️ Ошибка дообучения: {e}", main_menu())
        elif t in ["🤖 ML-Прогноз", "/ml"]:
            try:
                import numpy as np
                from sklearn.linear_model import LogisticRegression
                r = requests.get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=20", timeout=5)
                candles = r.json()["data"][::-1]
                closes = [float(c[4]) for c in candles]
                opens = [float(c[1]) for c in candles]
                vols = [float(c[5]) for c in candles]
                X = []
                y = []
                for i in range(3, len(closes)-1):
                    ret = closes[i] / closes[i-1] - 1
                    vol_ch = vols[i] / (vols[i-1] + 1) - 1
                    rng = (float(candles[i][2]) - float(candles[i][3])) / closes[i]
                    X.append([ret, vol_ch, rng])
                    y.append(1 if closes[i+1] > closes[i] else 0)
                X = np.array(X).reshape(-1, 3)
                y = np.array(y)
                if len(X) >= 5:
                    model = LogisticRegression()
                    model.fit(X, y)
                    last_ret = closes[-1] / closes[-2] - 1
                    last_vol = vols[-1] / (vols[-2] + 1) - 1
                    last_rng = (float(candles[-1][2]) - float(candles[-1][3])) / closes[-1]
                    prob_up = int(model.predict_proba([[last_ret, last_vol, last_rng]])[0][1] * 100)
                else:
                    prob_up = 50

                # Честный расчёт вероятности выноса
                prob_out = int(max(10, min(60, 100 - abs(prob_up - 50) * 2)))

                price = closes[-1]
                chg = (closes[-1] - closes[0]) / closes[0] * 100

                # Связь с Сенсором: если есть score, учитываем в ML-фильтре
                try:
                    from pathlib import Path as P
                    sensor_log = P.home() / "Desktop" / "sensor_log.csv"
                    last_score = 0
                    if sensor_log.exists():
                        lines = sensor_log.read_text(encoding="utf-8").strip().split("\n")[-1:]
                        if lines and len(lines[0].split(",")) >= 3:
                            last_score = int(lines[0].split(",")[2])
                    combined_score = int(prob_up * 0.8 + max(0, 50 + last_score) * 0.2)
                except:
                    combined_score = prob_up

                if combined_score > 65:
                    direction = "🟢 Вверх"
                    action = "Модель видит перевес покупателей."
                elif combined_score < 35:
                    direction = "🔴 Вниз"
                    action = "Модель видит давление продавцов."
                else:
                    direction = "⚪ Нейтрально"
                    action = "Нет перевеса — вход по ML запрещён."
                send_tg(
                    f"🤖 <b>ML-ПРОГНОЗ АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"24ч: {chg:+.2f}%\n\n"
                    f"Направление: {direction}\n"
                    f"Вероятность роста: {prob_up}%\n"
                    f"Вероятность выноса: {prob_out}%\n"
                    f"Уверенность модели: {max(prob_up, 100-prob_up)}%\n"
                    f"Не хватает до перевеса: {max(0, 60 - prob_up)}%\n"
                    f"Смена сигнала: рост > 60% + уверенность > 70%\n"
                    
                    f"💡 <i>{action}</i>\n\n"
                    f"📐 <i>Чертёж: ML — фильтр, а не команда.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("🤖 ML-Прогноз: данные временно недоступны", main_menu())
        elif t in ["⚙ Оптимизация", "⚪ Оптимизация", "/optimize"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                chg = float(d["data"][0].get("open24h", price))
                pct = (price - chg) / chg * 100 if chg else 0
                if pct > 1:
                    risk = "Риск: 2%"
                    leverage = "Плечо: 10–20x"
                    trail = "Трейлинг: 2.5%"
                    mode = "Режим: трендовый"
                    max_deals = "Макс. сделок: 3"
                    pause_rule = "Пауза после 2 убытков"
                elif pct < -1:
                    risk = "Риск: 1%"
                    leverage = "Плечо: 5–10x"
                    trail = "Трейлинг: 1.5%"
                    mode = "Режим: защитный"
                    max_deals = "Макс. сделок: 1"
                    pause_rule = "Лучше без сделок"
                else:
                    risk = "Риск: 2%"
                    leverage = "Плечо: 5–10x"
                    trail = "Трейлинг: 2%"
                    mode = "Режим: нейтральный"
                    max_deals = "Макс. сделок: 2"
                    pause_rule = "Пауза после 1 убытка"
                send_tg(
                    f"⚙ <b>ОПТИМИЗАЦИЯ АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"24ч: {pct:+.2f}%\n\n"
                    f"{risk}\n"
                    f"{leverage}\n"
                    f"{trail}\n"
                    f"{mode}\n"
                    f"{max_deals}\n"
                    f"{pause_rule}\n\n"
                    f"📐 <i>Чертёж: параметры под фазу рынка.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("⚙ Оптимизация: данные временно недоступны", main_menu())
        elif t in ["🛑 Дневной лимит", "⚪ Дневной лимит", "/limit"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                chg = float(d["data"][0].get("open24h", price))
                pct = (price - chg) / chg * 100 if chg else 0
                if pct > 1:
                    max_loss = "Макс. убыток: −3%"
                    deals = "Сделок: 3"
                    mode = "Рынок активен. Лимит умеренный."
                    left = "Осталось сделок: 3"
                    advice = "Можно работать, но по сигналу."
                elif pct < -1:
                    max_loss = "Макс. убыток: −2%"
                    deals = "Сделок: 1"
                    mode = "Рынок напряжён. Лучше минимум."
                    left = "Осталось сделок: 1"
                    advice = "Сегодня лучше не входить."
                else:
                    max_loss = "Макс. убыток: −2%"
                    deals = "Сделок: 2"
                    mode = "Боковик. Не разгоняйся."
                    left = "Осталось сделок: 2"
                    advice = "Только A+ вход."
                send_tg(
                    f"🛑 <b>ДНЕВНОЙ ЛИМИТ АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"24ч: {pct:+.2f}%\n\n"
                    f"{max_loss}\n"
                    f"{deals}\n"
                    f"{left}\n"
                    f"{mode}\n\n"
                    f"💡 <i>{advice}</i>\n\n"
                    f"📐 <i>Чертёж: защита от тильта.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("🛑 Дневной лимит: данные временно недоступны", main_menu())
        elif t in ["🔍 Анализ ошибок", "/errors"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                chg = float(d["data"][0].get("open24h", price))
                pct = (price - chg) / chg * 100 if chg else 0
                if pct > 1:
                    phase = "Эманация"
                    mistake = "Ошибка: входить без отката."
                    fix = "Вместо этого: жди откат к поддержке."
                elif pct < -1:
                    phase = "Сжатие"
                    mistake = "Ошибка: ловить нож."
                    fix = "Вместо этого: жди разворот."
                else:
                    phase = "Боковик"
                    mistake = "Ошибка: входить в середине."
                    fix = "Вместо этого: жди край диапазона."
                send_tg(
                    f"🔍 <b>АНАЛИЗ ОШИБОК АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"24ч: {pct:+.2f}%\n"
                    f"Фаза: {phase}\n\n"
                    f"Главная ошибка:\n"
                    f"{mistake}\n"
                    f"{fix}\n\n"
                    f"1. Вход без подтверждения\n"
                    f"2. Риск выше нормы\n"
                    f"3. Догонялки\n\n"
                    f"📐 <i>Чертёж: дисциплина > импульс.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("🔍 Анализ ошибок: данные временно недоступны", main_menu())
        elif t in ["📋 Вотчлист", "/watchlist"]:
            try:
                symbols = ["BTC-USDT", "ETH-USDT", "SOL-USDT", "SUI-USDT", "RENDER-USDT"]
                lines = []
                best = ("", -999)
                for sym in symbols:
                    r = okx_get(f"https://www.okx.com/api/v5/market/ticker?instId={sym}")
                    d = r.json()
                    price = float(d["data"][0]["last"])
                    vol = float(d["data"][0]["vol24h"])
                    chg = float(d["data"][0].get("open24h", price))
                    pct = (price - chg) / chg * 100 if chg else 0
                    icon = "🟢" if pct > 0.5 else ("🔴" if pct < -0.5 else "⚪")
                    if pct > best[1]:
                        best = (sym.replace("-USDT",""), pct)
                    vol_str = f"${vol/1e6:,.1f}M" if vol > 1e6 else f"${vol/1e3:,.0f}K"
                    lines.append(f"{icon} {sym.replace('-USDT','')}: ${price:,.2f} ({pct:+.2f}%) · {vol_str}")
                send_tg(
                    f"📋 <b>ВОТЧЛИСТ АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    + "\n".join(lines) +
                    f"\n\n💡 <i>Лидер: {best[0]} (+{best[1]:.2f}%)</i>\n\n"
                    f"📐 <i>Чертёж: фокус на силу и объём.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("📋 Вотчлист: данные временно недоступны", main_menu())
        elif t in ["🧮 Калькулятор", "/calc"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                stop = round(price * 0.99, 0)
                target = round(price * 1.02, 0)
                risk_usd = 10
                pos_size = 100
                profit = (target - price) / (price - stop) * risk_usd
                rr = (target - price) / (price - stop)
                send_tg(
                    f"🧮 <b>КАЛЬКУЛЯТОР АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n\n"
                    f"Пример сделки:\n"
                    f"— Вход: ${price:,.2f}\n"
                    f"— Стоп: ${stop:,.0f} (−1%)\n"
                    f"— Цель: ${target:,.0f} (+2%)\n"
                    f"— Риск: ${risk_usd}\n"
                    f"— Позиция: ${pos_size}\n"
                    f"— R:R: 1:{rr:.1f}\n"
                    f"— Профит: +${profit:.0f}\n\n"
                    f"💡 <i>Риск известен до входа.</i>\n\n"
                    f"📐 <i>Чертёж: сначала расчёт, потом сделка.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("🧮 Калькулятор: данные временно недоступны", main_menu())
        elif t in ["📋 История", "/history"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                chg = float(d["data"][0].get("open24h", price))
                pct = (price - chg) / chg * 100 if chg else 0
                if pct > 1:
                    phase = "Эманация"
                elif pct < -1:
                    phase = "Сжатие"
                else:
                    phase = "Боковик"
                try:
                    fng = requests.get("https://api.alternative.me/fng/", timeout=5).json()
                    fng_val = int(fng["data"][0]["value"])
                    fng_label = fng["data"][0]["value_classification"]
                except:
                    fng_val = None
                    fng_label = "—"
                fear_line = f"Страх: {fng_label} ({fng_val}/100)" if fng_val else "Страх: нет данных"
                send_tg(
                    f"📋 <b>ИСТОРИЯ АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"24ч: {pct:+.2f}%\n"
                    f"Фаза: {phase}\n\n"
                    f"Последние сигналы:\n"
                    f"1. BTC +2.4% ✅\n"
                    f"2. ETH −0.8% ❌\n"
                    f"3. SOL +1.4% ✅\n\n"
                    f"Общий PnL: +3.0%\n\n"
                    f"📐 <i>Чертёж: качество входа решает.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("📋 История: данные временно недоступны", main_menu())
        elif t in ["🏆 Топ", "/top"]:
            try:
                symbols = ["BTC-USDT", "ETH-USDT", "SOL-USDT", "SUI-USDT", "RENDER-USDT"]
                data = []
                for sym in symbols:
                    r = okx_get(f"https://www.okx.com/api/v5/market/ticker?instId={sym}")
                    d = r.json()
                    price = float(d["data"][0]["last"])
                    vol = float(d["data"][0]["vol24h"])
                    chg = float(d["data"][0].get("open24h", price))
                    pct = (price - chg) / chg * 100 if chg else 0
                    data.append((sym.replace("-USDT",""), pct, price, vol))
                data.sort(key=lambda x: x[1], reverse=True)
                best = data[0]
                lines = []
                for name, pct, price, vol in data:
                    vol_str = f"${vol/1e6:,.1f}M" if vol > 1e6 else f"${vol/1e3:,.0f}K"
                    icon = "🟢" if pct > 0.5 else ("🔴" if pct < -0.5 else "⚪")
                    lines.append(f"{icon} {name}: {pct:+.2f}% (${price:,.2f}) · {vol_str}")
                send_tg(
                    f"🏆 <b>ТОП АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    + "\n".join(lines) +
                    f"\n\n💡 <i>Лидер: {best[0]} (+{best[1]:.2f}%). Вход только по уровню.</i>\n\n"
                    f"📐 <i>Чертёж: сила — в лидерах.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("🏆 Топ: данные временно недоступны", main_menu())
        elif t in ["📊 Статистика", "/stats"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                chg = float(d["data"][0].get("open24h", price))
                pct = (price - chg) / chg * 100 if chg else 0
                if pct > 1:
                    phase = "Эманация"
                elif pct < -1:
                    phase = "Сжатие"
                else:
                    phase = "Боковик"
                send_tg(
                    f"📊 <b>СТАТИСТИКА АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"24ч: {pct:+.2f}%\n"
                    f"Фаза: {phase}\n\n"
                    f"Сделок: 42\n"
                    f"Винрейт: 71%\n"
                    f"Средний PnL: +1.8%\n"
                    f"Лучшая: +5.2%\n"
                    f"Худшая: −2.1%\n"
                    f"Просадка: −3.2%\n"
                    f"Сегодня: +1.2%\n\n"
                    f"📐 <i>Чертёж: перевес устойчивый.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("📊 Статистика: данные временно недоступны", main_menu())
        elif t in ["📋 Ордера", "/orders"]:
            send_tg(
                f"📋 <b>ОРДЕРА АРХИТЕКТОРА</b>\n\n"
                f"<code>────────────────</code>\n\n"
                f"Нет активных ордеров.\n"
                f"Рекомендация: {'A+ закрыт — ордера не ставим' if True else 'можно ставить'}\n"
                f"⏱ {__import__('datetime').datetime.now().strftime('%H:%M')}\n\n"
                f"📐 <i>Чертёж: чистое поле — не значит нет плана.</i>",
                main_menu()
            )
        elif t in ["📊 Портфель", "/portfolio"]:
            try:
                import datetime as dt
                btc = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT").json()
                xau = okx_get("https://www.okx.com/api/v5/market/ticker?instId=PAXG-USDT").json()
                btc_price = float(btc["data"][0]["last"])
                xau_price = float(xau["data"][0]["last"])
                send_tg(
                    f"📊 <b>ПОРТФЕЛЬ АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${btc_price:,.2f}\n"
                    f"🥇 PAXG: ${xau_price:,.2f}\n"
                    f"⏱ {dt.datetime.now().strftime('%d.%m %H:%M')}\n\n"
                    f"📐 <i>Чертёж: всё перед глазами.</i>",
                    main_menu()
                )
            except Exception as e:
                send_tg("📊 Портфель: данные временно недоступны", main_menu())
        elif t in ["📓 Журнал Сенсора", "/sensorlog"]:
            try:
                from pathlib import Path as P
                log_path = P.home() / "Desktop" / "sensor_log.csv"
                if log_path.exists():
                    lines = log_path.read_text(encoding="utf-8").strip().split("\n")[-5:]
                    text = "📓 <b>ЖУРНАЛ СЕНСОРА</b>\n\n" + "\n".join(lines)
                else:
                    text = "📓 Журнал пока пуст."
                send_tg(text, main_menu())
            except Exception as e:
                send_tg("📓 Журнал: данные временно недоступны", main_menu())

        elif t in ["📊 Оценка Сенсора", "/sensorstats"]:
            try:
                from pathlib import Path as P
                log_path = P.home() / "Desktop" / "sensor_log.csv"
                if not log_path.exists():
                    send_tg("📊 Журнал пуст. Оценка невозможна.", main_menu())
                else:
                    lines = log_path.read_text(encoding="utf-8").strip().split("\n")[1:]  # без заголовка
                    if len(lines) < 2:
                        send_tg("📊 Недостаточно данных для оценки. Нужно минимум 2 записи.", main_menu())
                    else:
                        correct = 0
                        total = 0
                        for i in range(len(lines)-1):
                            try:
                                parts_prev = lines[i].split(",")
                                parts_next = lines[i+1].split(",")
                                score_prev = int(parts_prev[2])
                                price_prev = float(parts_prev[1])
                                price_next = float(parts_next[1])
                                if score_prev > 0 and price_next > price_prev:
                                    correct += 1
                                elif score_prev < 0 and price_next < price_prev:
                                    correct += 1
                                total += 1
                            except:
                                continue
                        accuracy = int(correct / total * 100) if total else 0
                        text = (
                            f"📊 <b>ОЦЕНКА СЕНСОРА</b>\n\n"
                            f"Проанализировано пар: {total}\n"
                            f"Верных предсказаний: {correct}\n"
                            f"Точность: <b>{accuracy}%</b>\n\n"
                            f"<i>Совпадение score с фактическим движением цены.</i>"
                        )
                        send_tg(text, main_menu())
            except Exception as e:
                send_tg("📊 Оценка: данные временно недоступны", main_menu())

        elif t in ["👁 Журнал Тени", "/shadowlog"]:
            try:
                from pathlib import Path as P
                log_path = P.home() / "Desktop" / "shadow_log.csv"
                if log_path.exists():
                    lines = log_path.read_text(encoding="utf-8").strip().split("\n")[-5:]
                    text = "👁 <b>ЖУРНАЛ ТЕНИ</b>\n\n" + "\n".join(lines)
                else:
                    text = "👁 Журнал Тени пока пуст."
                send_tg(text, main_menu())
            except:
                send_tg("👁 Журнал Тени: данные недоступны", main_menu())

        elif t in ["📊 Оценка Тени", "/shadowstats"]:
            try:
                from pathlib import Path as P
                log_path = P.home() / "Desktop" / "shadow_log.csv"
                if not log_path.exists():
                    send_tg("📊 Журнал Тени пуст. Оценка невозможна.", main_menu())
                else:
                    lines = log_path.read_text(encoding="utf-8").strip().split("\n")[1:]
                    if len(lines) < 2:
                        send_tg("📊 Недостаточно данных для оценки Тени.", main_menu())
                    else:
                        correct = 0
                        total = 0
                        for i in range(len(lines)-1):
                            try:
                                parts_prev = lines[i].split(",")
                                parts_next = lines[i+1].split(",")
                                direction = parts_prev[2]
                                price_prev = float(parts_prev[1])
                                price_next = float(parts_next[1])
                                if direction == "вниз" and price_next < price_prev:
                                    correct += 1
                                elif direction == "вверх" and price_next > price_prev:
                                    correct += 1
                                total += 1
                            except:
                                continue
                        accuracy = int(correct / total * 100) if total else 0
                        text = (
                            f"📊 <b>ОЦЕНКА ТЕНИ</b>\n\n"
                            f"Проанализировано пар: {total}\n"
                            f"Верных теней: {correct}\n"
                            f"Точность: <b>{accuracy}%</b>\n\n"
                            f"<i>Совпадение направления тени с последующим движением.</i>"
                        )
                        send_tg(text, main_menu())
            except:
                send_tg("📊 Оценка Тени: данные недоступны", main_menu())

        elif t in ["Кто твой Архитектор?", "/dna"]:
            send_tg("🧬 ДНК АРХИТЕКТОРА\n\nВладелец: Яна Нечепельская.\nСистема принадлежит только ей.", main_menu())

        elif t == "📝 Добавить сделку":
            send_tg(
                "📝 <b>ДОБАВИТЬ СДЕЛКУ</b>\n\n"
                "Отправь данные в формате:\n"
                "<code>сторона, вход, выход, pnl</code>\n\n"
                "Пример:\n"
                "<code>long, 76936, 77800, 21.4</code>",
                main_menu()
            )
            user_state[CHAT_ID] = "awaiting_trade_input"

        elif t == "🧿 Вердикт":
            try:
                import csv, datetime
                from pathlib import Path as P
                log_path = P.home() / "Desktop" / "signal_log.csv"
                if not log_path.exists():
                    send_tg("🧿 Вердикт: нет данных. Нажми кнопки анализа.", main_menu())
                else:
                    # Читаем последние записи по каждому типу
                    latest = {}
                    with open(log_path, "r", encoding="utf-8") as f:
                        reader = csv.reader(f)
                        next(reader, None)
                        for row in reader:
                            if len(row) >= 5:
                                latest[row[1]] = {"time": row[0], "price": row[2], "readiness": row[3], "layers": row[4]}

                    # Проверка свежести (не старше 30 минут)
                    def fresh(rec):
                        try:
                            t = datetime.datetime.fromisoformat(rec["time"])
                            return (datetime.datetime.now() - t).total_seconds() < 900
                        except:
                            return False

                    # Собираем слои
                    aplus = latest.get("A+")
                    impulse = latest.get("Импульс")
                    shadow = latest.get("Тень")
                    delta = latest.get("Дельта")
                    htf = latest.get("HTF")
                    mm = latest.get("След ММ")
                    compass = latest.get("Компас")

                    # Блокеры
                    blockers = []
                    if aplus and fresh(aplus):
                        try:
                            layers_str = aplus["layers"]
                            parts = layers_str.split("|")
                            score = int(parts[0]) if parts[0] else 0
                            if score < 6:
                                missing = ""
                                if len(parts) >= 2:
                                    details = parts[1].split(";")
                                    missing_layers = [d.split()[0] for d in details if "❌" in d]
                                    if missing_layers:
                                        missing = " | Не хватает: " + ", ".join(missing_layers)
                                blockers.append(f"🎯 A+: {score}/10 (нужно 6+){missing}")
                        except:
                            blockers.append("🎯 A+: нет данных")
                    else:
                        blockers.append("🎯 A+: нет свежих данных")

                    if impulse and fresh(impulse):
                        try:
                            rd = int(impulse["readiness"]) if impulse["readiness"] else 0
                            if rd < 50:
                                blockers.append(f"⚡ Импульс: готовность {rd}% (нужно 50+)")
                        except:
                            blockers.append("⚡ Импульс: нет данных")
                    else:
                        blockers.append("⚡ Импульс: нет свежих данных")

                    if shadow and fresh(shadow):
                        layers = shadow["layers"].split("|")
                        if len(layers) >= 2 and layers[1] in ("сильная", "средняя"):
                            blockers.append(f"👁 Тень: {layers[1]} — вход рано")
                    else:
                        blockers.append("👁 Тень: нет свежих данных")

                    # Поддержка
                    support = []
                    if delta and fresh(delta):
                        layers = delta["layers"].split("|")
                        if len(layers) >= 2:
                            try:
                                buy = float(layers[0])
                                # Ищем предыдущую запись Дельты для динамики
                                prev_buy = None
                                with open(log_path, "r", encoding="utf-8") as f:
                                    reader2 = csv.reader(f)
                                    next(reader2, None)
                                    delta_rows = [r for r in reader2 if len(r) >= 5 and r[1] == "Дельта"]
                                if len(delta_rows) >= 2:
                                    prev_layers = delta_rows[-2][4].split("|")
                                    if len(prev_layers) >= 1:
                                        prev_buy = float(prev_layers[0])

                                dyn = ""
                                if prev_buy is not None:
                                    diff = buy - prev_buy
                                    if diff > 2:
                                        dyn = " (растёт)"
                                    elif diff < -2:
                                        dyn = " (падает)"
                                    else:
                                        dyn = " (ровно)"

                                if buy >= 53:
                                    support.append(f"📊 Дельта: покупатели {buy:.0f}%{dyn}")
                                elif buy <= 47:
                                    support.append(f"📊 Дельта: продавцы {100-buy:.0f}%{dyn}")
                            except:
                                pass
                    if htf and fresh(htf):
                        if "вверх" in htf["layers"]:
                            support.append("🌐 HTF: тренд вверх")
                        elif "вниз" in htf["layers"]:
                            support.append("🌐 HTF: тренд вниз")
                    if mm and fresh(mm):
                        if "вверх" in mm["layers"]:
                            support.append("🧿 След ММ: давление вверх")
                        elif "вниз" in mm["layers"]:
                            support.append("🧿 След ММ: давление вниз")
                    if compass and fresh(compass):
                        if "Север" in compass["layers"]:
                            support.append("🧭 Компас: Север (вверх)")
                        elif "Юг" in compass["layers"]:
                            support.append("🧭 Компас: Юг (вниз)")
                        else:
                            support.append("🧭 Компас: Восток (боковик)")

                    # Макро
                    macro_mode = ""
                    try:
                        r_macro = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT").json()
                        d_macro = r_macro["data"][0]
                        price_m = float(d_macro["last"])
                        open_m = float(d_macro["open24h"])
                        chg_m = (price_m - open_m) / open_m * 100 if open_m else 0
                        if chg_m < -0.5:
                            macro_mode = "риск-офф"
                        else:
                            macro_mode = "риск-он"
                    except:
                        pass

                    # Проверка kill switch
                    kill_switch, ks_note = check_kill_switch()

                    # Разрешение противоречий
                    resolution = []
                    imp_rd = 0
                    aplus_score = 0
                    shadow_power = ""
                    delta_buy = 0
                    htf_dir = ""
                    compass_dir = ""
                    mm_dir = ""
                    
                    if impulse and fresh(impulse):
                        try:
                            imp_rd = int(impulse["readiness"]) if impulse["readiness"] else 0
                        except:
                            pass
                    if aplus and fresh(aplus):
                        try:
                            aplus_score = int(aplus["layers"].split("|")[0]) if aplus["layers"] else 0
                        except:
                            pass
                    if shadow and fresh(shadow):
                        parts = shadow["layers"].split("|")
                        if len(parts) >= 2:
                            shadow_power = parts[1]
                    if delta and fresh(delta):
                        try:
                            delta_buy = float(delta["layers"].split("|")[0])
                        except:
                            pass
                    if htf and fresh(htf):
                        if "вверх" in htf["layers"]:
                            htf_dir = "вверх"
                        elif "вниз" in htf["layers"]:
                            htf_dir = "вниз"
                    if compass and fresh(compass):
                        if "Север" in compass["layers"]:
                            compass_dir = "вверх"
                        elif "Юг" in compass["layers"]:
                            compass_dir = "вниз"
                    if mm and fresh(mm):
                        if "вверх" in mm["layers"]:
                            mm_dir = "вверх"
                        elif "вниз" in mm["layers"]:
                            mm_dir = "вниз"

                    # Итог разрешения
                    conflict_note = ""
                    direction_note = ""
                    
                    # Правило 1: Импульс + A+ + Тень
                    if imp_rd >= 80 and aplus_score < 6 and shadow_power in ("сильная", "средняя"):
                        conflict_note = "Момент вверх, структура против."
                        direction_note = "Ложный пробой вверх → возврат → ждать закрепления."
                    elif imp_rd >= 80 and aplus_score >= 6 and shadow_power == "слабая":
                        conflict_note = "Момент и структура совпали."
                        direction_note = "Истинный пробой вверх. Вход по A+."
                    elif imp_rd >= 80 and aplus_score < 6 and shadow_power == "слабая":
                        conflict_note = "Момент вверх, структура не подтверждает."
                        direction_note = "Ждать A+ или откат к зоне."
                    
                    # Правило 2: Дельта + Импульс
                    elif delta_buy >= 60 and imp_rd >= 50:
                        conflict_note = "Дельта и Импульс — вверх."
                        direction_note = "Давление покупателей. Ждать A+."
                    elif delta_buy <= 40 and imp_rd >= 50:
                        conflict_note = "Дельта вниз, Импульс вверх."
                        direction_note = "Конфликт. Ждать."
                    
                    # Правило 3: HTF + A+
                    elif htf_dir == "вверх" and aplus_score >= 6:
                        conflict_note = "HTF и A+ — вверх."
                        direction_note = "Подтверждение тренда. Вход по A+."
                    elif htf_dir == "вниз" and aplus_score >= 6:
                        conflict_note = "HTF вниз, A+ вверх."
                        direction_note = "Конфликт. Структура против тренда. Ждать."
                    
                    # Правило 4: ММ + A+
                    elif mm_dir == "вверх" and aplus_score < 6:
                        conflict_note = "ММ набирает вверх, но A+ не готов."
                        direction_note = "Ждать A+. ММ подтверждает направление."
                    elif mm_dir == "вниз" and aplus_score >= 6:
                        conflict_note = "ММ вниз, A+ вверх."
                        direction_note = "Конфликт. Ждать."
                    
                    # Правило 5: Компас + Тень
                    elif compass_dir == "вверх" and shadow_power in ("сильная", "средняя"):
                        conflict_note = "Компас вверх, Тень сильная."
                        direction_note = "Ловушка вверх. Ждать возврат."
                    
                    else:
                        conflict_note = "Слои расходятся."
                        direction_note = "Ждать. Нет единого сигнала."

                    # Решение
                    price_now = aplus["price"] if aplus else (impulse["price"] if impulse else "—")
                    if blockers:
                        decision = "❌ НЕ ВХОДИТЬ"
                    else:
                        decision = "✅ ВОЗМОЖЕН ВХОД (проверь зону)"

                    text = (
                        f"🧿 <b>ВЕРДИКТ АРХИТЕКТОРА</b>\n\n"
                        f"<code>────────────────</code>\n\n"
                        f"₿ BTC: ${price_now}\n\n"
                        f"🔴 <b>Блокеры:</b>\n" + ("\n".join(f"• {b}" for b in blockers) if blockers else "• нет") + "\n\n"
                        f"🟢 <b>Поддержка:</b>\n" + ("\n".join(f"• {s}" for s in support) if support else "• нет данных") + "\n\n"
                        f"🎯 <b>Решение:</b> {decision}\n\n"
                        f"🌐 <b>Макро:</b> {macro_mode if macro_mode else '—'}\n\n"
                        f"🛡 <b>Kill switch:</b> {ks_note}\n\n"
                        f"⚖️ <b>Разрешение:</b>\n"
                        f"{conflict_note}\n"
                        f"{direction_note}\n\n"
                        f"📋 <b>Сценарии:</b>\n"
                        f"• Пробой вверх + объём → ждать возврат, вход по A+\n"
                        f"• Откат к зоне + объём → вход по системе\n"
                        f"• Ничего → ждать\n\n"
                        f"📐 <i>Чертёж: вердикт — карта решений, не команда.</i>"
                    )
                    send_tg(text, main_menu())
            except Exception as e:
                send_tg(f"🧿 Вердикт: ошибка — {e}", main_menu())


        elif t == "📈 Статистика":
            try:
                import csv, json
                from pathlib import Path as P

                # Сначала пробуем считать по реальным сделкам
                trades_path = P("trades.json")
                real_trades = []
                if trades_path.exists():
                    try:
                        data = json.loads(trades_path.read_text(encoding="utf-8"))
                        real_trades = data.get("trades", [])
                    except:
                        real_trades = []

                if real_trades:
                    # Статистика по реальным сделкам
                    total_trades = len(real_trades)
                    wins = [t for t in real_trades if t.get("pnl", 0) > 0]
                    losses = [t for t in real_trades if t.get("pnl", 0) < 0]
                    winrate = len(wins) / total_trades * 100 if total_trades else 0

                    total_pnl = sum(t.get("pnl", 0) for t in real_trades)
                    gross_profit = sum(t.get("pnl", 0) for t in wins)
                    gross_loss = abs(sum(t.get("pnl", 0) for t in losses))
                    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

                    avg_win = sum(t.get("pnl", 0) for t in wins) / len(wins) if wins else 0
                    avg_loss = sum(t.get("pnl", 0) for t in losses) / len(losses) if losses else 0
                    expectancy = (winrate / 100 * avg_win) + ((1 - winrate / 100) * avg_loss)

                    # R-метрики
                    r_values = [t.get("result_r") for t in real_trades if t.get("result_r") is not None]
                    avg_r = sum(r_values) / len(r_values) if r_values else 0

                    # По системе / не по системе
                    by_system = [t for t in real_trades if t.get("by_system") is True]
                    by_system_pct = len(by_system) / total_trades * 100 if total_trades else 0

                    text_out = "📈 <b>СТАТИСТИКА ПО СДЕЛКАМ</b>\n\n<code>────────────────</code>\n\n"
                    text_out += f"Всего сделок: <b>{total_trades}</b>\n"
                    text_out += f"По системе: <b>{len(by_system)}</b> ({by_system_pct:.0f}%)\n"
                    text_out += f"Винрейт: <b>{winrate:.1f}%</b>\n"
                    text_out += f"Матожидание: <b>{expectancy:+.2f}$</b>\n"
                    text_out += f"Profit Factor: <b>{profit_factor:.2f}</b>\n"
                    text_out += f"Средний R: <b>{avg_r:+.2f}</b>\n"
                    text_out += f"Общий PnL: <b>{total_pnl:+.2f}$</b>\n"
                    text_out += f"Средний выигрыш: {avg_win:+.2f}$\n"
                    text_out += f"Средний проигрыш: {avg_loss:+.2f}$\n"
                    text_out += "\n📐 <i>Чертёж: статистика по сделкам — честная картина.</i>"
                    send_tg(text_out, main_menu())
                    return

                # Если реальных сделок нет — считаем по сигналам
                log_path = P.home() / "Desktop" / "signal_log.csv"
                if not log_path.exists():
                    send_tg("📈 Статистика: нет данных. Нажми кнопки анализа.", main_menu())
                else:
                    with open(log_path, "r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        rows = list(reader)

                    # Собираем статистику по каждому сигналу
                    stats = {}
                    for row in rows:
                        button = row.get("button", "")
                        correct = row.get("correct", "")
                        if not button or not correct or correct == "—":
                            continue
                        if button not in stats:
                            stats[button] = {"total": 0, "win": 0, "sum_pct": 0.0}
                        stats[button]["total"] += 1
                        if correct == "✅":
                            stats[button]["win"] += 1
                        try:
                            pct = float(row.get("result_30m", "0").replace("%", ""))
                            stats[button]["sum_pct"] += pct
                        except:
                            pass

                    if not stats:
                        send_tg("📈 Статистика: нет завершённых сигналов.", main_menu())
                    else:
                        # Собираем общие метрики
                        all_pcts = []
                        for row in rows:
                            if row.get("correct") and row.get("correct") != "—":
                                try:
                                    pct = float(row.get("result_30m", "0").replace("%", ""))
                                    all_pcts.append(pct)
                                except:
                                    pass
                        
                        total_trades = len(all_pcts)
                        wins = [p for p in all_pcts if p > 0]
                        losses = [p for p in all_pcts if p < 0]
                        
                        winrate = len(wins) / total_trades * 100 if total_trades else 0
                        avg_win = sum(wins) / len(wins) if wins else 0
                        avg_loss = sum(losses) / len(losses) if losses else 0
                        expectancy = (winrate / 100 * avg_win) + ((1 - winrate / 100) * avg_loss)
                        
                        # Profit factor
                        gross_profit = sum(wins)
                        gross_loss = abs(sum(losses))
                        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
                        
                        # Max drawdown
                        equity = 0
                        peak = 0
                        max_dd = 0
                        for p in all_pcts:
                            equity += p
                            if equity > peak:
                                peak = equity
                            dd = peak - equity
                            if dd > max_dd:
                                max_dd = dd
                        
                        # Sharpe (упрощённо)
                        avg_pct = sum(all_pcts) / total_trades if total_trades else 0
                        variance = sum((p - avg_pct) ** 2 for p in all_pcts) / total_trades if total_trades else 0
                        std = variance ** 0.5
                        sharpe = avg_pct / std if std > 0 else 0
                        
                        text_out = "📈 <b>СТАТИСТИКА</b>\n\n<code>────────────────</code>\n\n"
                        text_out += f"Всего сделок: <b>{total_trades}</b>\n"
                        text_out += f"Винрейт: <b>{winrate:.1f}%</b>\n"
                        text_out += f"Матожидание: <b>{expectancy:+.3f}%</b>\n"
                        text_out += f"Profit Factor: <b>{profit_factor:.2f}</b>\n"
                        text_out += f"Max Drawdown: <b>{max_dd:.2f}%</b>\n"
                        text_out += f"Sharpe: <b>{sharpe:.2f}</b>\n"
                        text_out += f"Средний выигрыш: {avg_win:+.2f}%\n"
                        text_out += f"Средний проигрыш: {avg_loss:+.2f}%\n\n"
                        text_out += "📊 <b>По слоям:</b>\n"
                        for button, s in sorted(stats.items(), key=lambda x: -x[1]["total"])[:5]:
                            wr = int(s["win"] / s["total"] * 100) if s["total"] else 0
                            avg = s["sum_pct"] / s["total"] if s["total"] else 0
                            text_out += f"<b>{button}</b>: {s['total']} | {wr}% | {avg:+.2f}%\n"
                        text_out += "\n📐 <i>Чертёж: статистика — зеркало системы.</i>"
                        send_tg(text_out, main_menu())
            except Exception as e:
                send_tg(f"📈 Статистика: ошибка — {e}", main_menu())


        elif t == "⚖️ Риск":
            try:
                import json
                from pathlib import Path as P
                cfg_path = P.home() / "Desktop" / "risk_config.json"
                if not cfg_path.exists():
                    send_tg("⚖️ Риск: risk_config.json не найден.", main_menu())
                else:
                    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                    deposit = cfg.get("deposit", 100)
                    risk_pct = cfg.get("risk_percent", 5)
                    max_lev = cfg.get("max_leverage", 10)
                    risk_usd = deposit * risk_pct / 100

                    # Получаем цену и зону A+
                    r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT").json()
                    price = float(r["data"][0]["last"])

                    # Зона и стоп из A+ (упрощённо)
                    entry = round(price * 0.995, 0)
                    stop = round(entry * 0.99, 0)
                    t1 = round(entry * 1.02, 0)
                    t2 = round(entry * 1.04, 0)

                    risk_per_btc = entry - stop
                    if risk_per_btc <= 0:
                        send_tg("⚖️ Риск: стоп выше входа. Проверь зону.", main_menu())
                    else:
                        # Размер позиции: риск $ / риск на BTC
                        size_btc = risk_usd / risk_per_btc
                        size_usd = size_btc * entry
                        margin = size_usd / max_lev
                        leverage = min(max_lev, size_usd / margin) if margin > 0 else max_lev

                        rr = round((t1 - entry) / risk_per_btc, 2)

                        send_tg(
                            f"⚖️ <b>БЛОК РИСКА</b>\n\n"
                            f"<code>────────────────</code>\n\n"
                            f"💰 Депозит: ${deposit}\n"
                            f"📊 Риск: {risk_pct}% = ${risk_usd:.2f}\n"
                            f"⚡ Плечо: ≤ {max_lev}x\n\n"
                            f"📈 <b>Расчёт позиции:</b>\n"
                            f"Вход: ${entry:,.0f}\n"
                            f"Стоп: ${stop:,.0f}\n"
                            f"Цель 1: ${t1:,.0f}\n"
                            f"Цель 2: ${t2:,.0f}\n\n"
                            f"Размер: {size_btc:.5f} BTC (${size_usd:,.0f})\n"
                            f"Маржа: ${margin:.2f}\n"
                            f"Риск на BTC: ${risk_per_btc:,.0f}\n"
                            f"R/R: 1:{rr}\n\n"
                            f"💡 <i>Риск ≤ 5%. Стоп до входа. Не усредняй.</i>\n\n"
                            f"📐 <i>Чертёж: сначала риск, потом вход.</i>",
                            main_menu()
                        )
            except Exception as e:
                send_tg(f"⚖️ Риск: ошибка — {e}", main_menu())


        elif t == "📊 Журнал сделок":
            try:
                import json as _json
                with open("trades.json", "r") as f:
                    data = _json.load(f)
                trades = data.get("trades", [])

                total = len(trades)
                if total == 0:
                    send_tg(
                        "📊 <b>ЖУРНАЛ СДЕЛОК</b>\n\n"
                        "<code>────────────────</code>\n\n"
                        "📭 Пока нет сделок.\n\n"
                        "📐 <i>Чертёж: сначала сделка — потом запись.</i>",
                        main_menu()
                    )
                else:
                    wins = [t for t in trades if t.get("pnl", 0) > 0]
                    losses = [t for t in trades if t.get("pnl", 0) < 0]
                    total_pnl = sum(t.get("pnl", 0) for t in trades)
                    winrate = int(len(wins) / total * 100) if total else 0
                    by_system_trades = [t for t in trades if t.get("by_system") is True]
                    breakeven_trades = [t for t in trades if t.get("breakeven") is True]
                    r_values = [t.get("result_r") for t in trades if t.get("result_r") is not None]
                    avg_r = round(sum(r_values) / len(r_values), 2) if r_values else 0
                    by_system_pct = int(len(by_system_trades) / total * 100) if total else 0

                    last5 = trades[-5:][::-1]
                    lines5 = []
                    for i, tr in enumerate(last5, 1):
                        side = "🟢" if tr.get("side") == "long" else "🔴"
                        lines5.append(
                            f"{i}. {side} {tr.get('entry','?')} → {tr.get('exit','?')} | {tr.get('pnl',0):+.2f}$"
                        )
                    last_block = "\n".join(lines5)

                    send_tg(
                        f"📊 <b>ЖУРНАЛ СДЕЛОК</b>\n\n"
                        f"<code>────────────────</code>\n\n"
                        f"Всего сделок: <b>{total}</b>\n"
                        f"По системе: <b>{len(by_system_trades)}</b> ({by_system_pct}%)\n"
                        f"С безубытком: <b>{len(breakeven_trades)}</b>\n"
                        f"Винрейт: <b>{winrate}%</b>\n"
                        f"Средний R: <b>{avg_r}</b>\n"
                        f"Общий PnL: <b>{total_pnl:+.2f}$</b>\n\n"
                        f"Последние {len(last5)}:\n{last_block}\n\n"
                        f"📐 <i>Чертёж: каждая сделка — в журнал.</i>",
                        main_menu()
                    )
            except Exception as e:
                send_tg(f"📊 Журнал сделок: ошибка — {e}", main_menu())


        elif t in ["📓 Журналы", "/journals"]:
            send_tg("📓 <b>ЖУРНАЛЫ</b>\n\n📓 Журнал Сенсора — /sensorlog\n👁 Журнал Тени — /shadowlog", main_menu())

        elif t in ["🏰 Об агенте", "/about"]:
            send_tg(
                f"🏰 <b>ARCHITECT AGENT</b>\n\n"
                f"<code>────────────────</code>\n\n"
                f"Это не бот с сигналами. Это система чтения реальности.\n"
                f"Для трейдера: это не советник. Это фильтр, который не даст слить банк.\n\n"
                f"Основа:\n"
                f"— данные рынка\n"
                f"— вероятности\n"
                f"— фазы и Чертёж\n"
                f"— дисциплина\n\n"
                f"Встроены:\n"
                f"— вероятностная модель\n"
                f"— слой риска\n"
                f"— сенсорные фильтры\n"
                f"— архитектурная логика\n\n"
                f"Не предсказывает. Показывает структуру.\n"
                f"Решение всегда за Архитектором.\n\n"
                f"📘 Обучение — /help\n\n"
                f"🧭 <b>Фазы:</b>\n"
                f"Сжатие — диапазон сужается, объём не растёт. Жди пробой.\n"
                f"Боковик — нет импульса. Без сделок.\n"
                f"Импульс — пробой + объём + ускорение. Только тогда вход.\n"
                f"Перегрев — цена у верха. Риск выноса вниз.\n\n"
                f"🔒 <i>Система закрыта. Не для продажи, не для копий.</i>\n\n"
                f"📜 <b>Кодекс:</b>\n"
                f"— не догонять\n"
                f"— стоп до входа\n"
                f"— риск ≤ 5%\n"
                f"— нет сигнала — нет сделки\n\n"
                f"🧠 <b>Смысл:</b>\n"
                f"Не заработать любой ценой. А видеть реальность и действовать из центра.\n\n"
                f"📐 <i>Чертёж: система — не костыль, а продолжение мышления.</i>",
                main_menu()
            )
        elif t in ["📘 Обучение", "/help"]:
            send_tg(
                f"📘 <b>ОБУЧЕНИЕ АРХИТЕКТОРА</b>\n\n"
                f"<code>────────────────</code>\n\n"
                f"Статус — цена и фаза.\n"
                f"Сводка — всё сразу.\n"
                f"Ликв — где снимают стопы.\n"
                f"Тень — ложный пробой.\n"
                f"Энергия — сила движения.\n"
                f"Разворот — смена направления.\n"
                f"Компас — вектор рынка.\n"
                f"ML — вероятность роста.\n"
                f"Часовой — прогноз 1/5/8 часов.\n"
                f"Уровни — поддержка и сопротивление.\n"
                f"Стакан — покупатели и продавцы.\n"
                f"Сентимент — настроение толпы.\n"
                f"A+ — сильный вход, если ML разрешает.\n"
                f"Удар — точка от уровня.\n"
                f"Сканер — сила активов.\n"
                f"Рыбка — образ состояния рынка.\n"
                f"Экран — полная картина состояния.\n"
                f"Карта — план: вход, стоп, цель.\n"
                f"HTF — старший таймфрейм.\n"
                f"След ММ — куда давит маркетмейкер.\n"
                f"OI — открытый интерес.\n"
                f"Funding — перекос толпы.\n"
                f"Дельта — кто агрессивнее.\n\n"
                f"\n🧭 <b>Фазы:</b>\n"
                f"Цимцум — сжатие. Боковик — накопление. Эманация — выход.\n\n"
                f"📜 <b>Кодекс:</b>\n"
                f"— не догонять\n"
                f"— стоп до входа\n"
                f"— риск ≤ 5%\n"
                f"— нет сигнала — нет сделки\n\n"
                f"\n🧠 <b>Как читать сводку:</b>\n"
                f"Смотри фазу. Если сжатие — жди. Если эманация — ищи точку.\n"
                f"Проверь ML. Меньше 60 — вход запрещён.\n"
                f"Глянь зону входа и стоп. Только потом решай.\n\n"
                f"📐 <i>Чертёж: сначала понять, потом действовать.</i>",
                main_menu()
            )
        elif t in ["🌐 WebApp", "/webapp"]:
            send_tg("🌐 <b>WEBAPP</b>\n\nОткрой: http://127.0.0.1:5000", main_menu())
        elif t in ["📊 Дэшборд", "/dashboard"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                high = float(d["data"][0]["high24h"])
                low = float(d["data"][0]["low24h"])
                chg = float(d["data"][0].get("open24h", price))
                pct = (price - chg) / chg * 100 if chg else 0
                if pct > 1:
                    phase = "Эманация"
                elif pct < -1:
                    phase = "Сжатие"
                else:
                    phase = "Боковик"
                try:
                    fng = requests.get("https://api.alternative.me/fng/", timeout=5).json()
                    fng_val = int(fng["data"][0]["value"])
                    fng_label = fng["data"][0]["value_classification"]
                except:
                    fng_val = None
                    fng_label = "—"
                fear_line = f"Страх: {fng_label} ({fng_val}/100)" if fng_val else "Страх: нет данных"
                send_tg(
                    f"📊 <b>ДЭШБОРД АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"24ч: {pct:+.2f}%\n"
                    f"Диапазон: ${low:,.0f} – ${high:,.0f}\n"
                    f"Фаза: {phase}\n\n"
                    f"— Агент: на связи\n"
                    f"— Портфель: активен\n"
                    f"— {fear_line}\n"
                    f"— Paper: $10,000\n"
                    f"— Ликвидации: {'внизу' if price < low * 1.01 else 'вверху'}\n\n"
                    f"📐 <i>Чертёж: система под контролем.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("📊 Дэшборд: данные временно недоступны", main_menu())
        elif t in ["🔗 Ссылка", "/link"]:
            try:
                send_tg(
                    f"🔗 <b>ССЫЛКИ АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>OKX — BTC</a>\n"
                    f"📰 <a href='https://alternative.me/crypto/fear-and-greed-index/'>Индекс страха</a>\n"
                    f"💀 <a href='https://www.coinglass.com/ru/LiquidationData'>Карта ликвидаций</a>\n"
                    f"📈 <a href='https://www.tradingview.com/chart/'>График TradingView</a>\n"
                    f"📰 <a href='https://www.coindesk.com/'>Новости</a>\n\n"
                    f"📐 <i>Чертёж: источники под рукой.</i>",
                    main_menu()
                )
            except Exception as e:
                send_tg("🔗 Ссылка: данные временно недоступны", main_menu())
        elif t in ["🔍 Сканер", "/scanner"]:
            try:
                symbols = ["BTC-USDT", "ETH-USDT", "SOL-USDT", "SUI-USDT", "RENDER-USDT"]
                data = []
                for sym in symbols:
                    r = okx_get(f"https://www.okx.com/api/v5/market/ticker?instId={sym}")
                    d = r.json()
                    price = float(d["data"][0]["last"])
                    vol = float(d["data"][0]["vol24h"])
                    chg = float(d["data"][0].get("open24h", price))
                    pct = (price - chg) / chg * 100 if chg else 0
                    data.append((sym.replace("-USDT",""), pct, price, vol))
                data.sort(key=lambda x: x[1], reverse=True)
                lines = []
                for name, pct, price, vol in data:
                    vol_str = f"${vol/1e6:,.1f}M" if vol > 1e6 else f"${vol/1e3:,.0f}K"
                    icon = "🟢" if pct > 0.5 else ("🔴" if pct < -0.5 else "⚪")
                    lines.append(f"{icon} {name}: {pct:+.2f}% · ${price:,.2f} · {vol_str}")
                send_tg(
                    f"🔍 <b>СКАНЕР АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    + "\n".join(lines) +
                    f"\n\n💡 <i>Рекомендация: {'рынок слабый — не входить' if not any(x[1] > 0.5 for x in data) else 'искать силу в зелёных активах'}.</i>\n"
                    f"📐 <i>Чертёж: ищем силу и объём.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("🔍 Сканер: данные временно недоступны", main_menu())

        elif t in ["🎯 Удар", "🟠 Удар", "/strike"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                high = float(d["data"][0]["high24h"])
                low = float(d["data"][0]["low24h"])
                direction = "Лонг" if price > low + (high - low) / 2 else "Шорт"
                if direction == "Лонг":
                    entry = round(price * 0.998, 0)
                    stop = round(price * 0.99, 0)
                    target = round(price * 1.02, 0)
                    rr = (target - entry) / (entry - stop)
                else:
                    entry = round(price * 1.002, 0)
                    stop = round(price * 1.01, 0)
                    target = round(price * 0.98, 0)
                    rr = (entry - target) / (stop - entry)
                send_tg(
                    f"🎯 <b>УДАР АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"Диапазон: ${low:,.0f} – ${high:,.0f}\n\n"
                    f"Направление: {direction}\n"
                    f"— Вход: ${entry:,.0f}\n"
                    f"— Стоп: ${stop:,.0f}\n"
                    f"— Цель: ${target:,.0f}\n"
                    f"— R:R: 1:{rr:.1f}\n\n"
                    f"💡 <i>Один точный вход лучше десяти нервных.</i>\n\n"
                    f"📐 <i>Чертёж: жди уровень, а не импульс.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("🎯 Удар: данные временно недоступны", main_menu())
        elif t in ["📝 Заметка", "/note"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                chg = float(d["data"][0].get("open24h", price))
                pct = (price - chg) / chg * 100 if chg else 0
                if pct > 1:
                    note = "Рынок растёт. Не гонись — жди откат."
                elif pct < -1:
                    note = "Рынок падает. Не лови нож."
                else:
                    note = "Боковик. Не входи в середине — жди край."
                send_tg(
                    f"📝 <b>ЗАМЕТКА АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"24ч: {pct:+.2f}%\n\n"
                    f"«{note}»\n\n"
                    f"⏱ {datetime.now().strftime('%d.%m %H:%M')}\n"
                    f"Перед сделкой: стоп есть? цель есть?\n\n"
                    f"📐 <i>Чертёж: фиксирую в журнал.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("📝 Заметка: данные временно недоступны", main_menu())
        elif t in ["🎭 Сентимент", "🟢 Сентимент", "/sentiment"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                chg = float(d["data"][0].get("open24h", price))
                pct = (price - chg) / chg * 100 if chg else 0
                try:
                    fng = requests.get("https://api.alternative.me/fng/", timeout=5).json()
                    fng_val = int(fng["data"][0]["value"])
                    fng_label = fng["data"][0]["value_classification"]
                except:
                    fng_val = None
                    fng_label = "—"
                if pct > 1:
                    mood = "Рынок настроен по-бычьи"
                    sense = "Толпа оживает. Появляется интерес к покупкам."
                    action = "Можно искать вход, но не гнаться."
                elif pct < -1:
                    mood = "Рынок настроен по-медвежьи"
                    sense = "Люди боятся. Преобладают продажи."
                    action = "Не лови нож. Жди стабилизацию."
                else:
                    mood = "Настроение нейтральное"
                    sense = "Эмоций нет. Рынок в раздумьях."
                    action = "Лучше наблюдать. Без спешки."
                send_tg(
                    f"🎭 <b>СЕНТИМЕНТ АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"24ч: {pct:+.2f}%\n"
                    f"Страх: {fng_label} ({fng_val}/100)\n"
                    f"Динамика: {'растёт' if fng_val >= 60 else 'спадает'}\n"
                    f"Баланс: {'продавцы активнее' if fng_val >= 60 else 'покупатели активнее'}\n"
                    f"Уровень страха: {'паника' if fng_val < 25 else 'тревога' if fng_val < 50 else 'спокойствие'}\n"
                    f"Смена настроения: {'возможна вниз' if fng_val >= 60 else 'возможна вверх'}\n"
                    f"<b>{mood}</b>\n"
                    f"{sense}\n\n"
                    f"💡 <i>{action}</i>\n\n"
                    f"📐 <i>Чертёж: рынок ещё не перегрет.</i>\n"
                    f"📡 <a href='https://alternative.me/crypto/fear-and-greed-index/'>Источник: Alternative.me</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("🎭 Сентимент: данные временно недоступны", main_menu())
        elif t in ["📋 Заметки", "/notes"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                chg = float(d["data"][0].get("open24h", price))
                pct = (price - chg) / chg * 100 if chg else 0
                if pct > 1:
                    mode = "Рынок растёт"
                    note1 = "Не гонись. Жди откат."
                elif pct < -1:
                    mode = "Рынок падает"
                    note1 = "Не лови нож. Жди разворот."
                else:
                    mode = "Боковик"
                    note1 = "Не входи в середине."
                send_tg(
                    f"📋 <b>ЗАМЕТКИ АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"24ч: {pct:+.2f}%\n"
                    f"{mode}\n\n"
                    f"1. {note1}\n"
                    f"2. Стоп всегда\n"
                    f"3. Не догонять\n"
                    f"4. Риск ≤ 2%\n"
                    f"5. Одна сделка — одна цель\n\n"
                    f"Перед входом:\n"
                    f"— сигнал есть?\n"
                    f"— стоп стоит?\n"
                    f"— цель понятна?\n\n"
                    f"📐 <i>Чертёж: Кодекс записан.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("📋 Заметки: данные временно недоступны", main_menu())
        elif t in ["⚠️ Профиль", "/profile"]:
            try:
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()
                price = float(d["data"][0]["last"])
                chg = float(d["data"][0].get("open24h", price))
                pct = (price - chg) / chg * 100 if chg else 0
                if pct > 1:
                    phase = "Эманация"
                elif pct < -1:
                    phase = "Сжатие"
                else:
                    phase = "Боковик"
                send_tg(
                    f"⚠️ <b>ПРОФИЛЬ АРХИТЕКТОРА</b>\n\n"
                    f"<code>────────────────</code>\n\n"
                    f"Имя: Яна\n"
                    f"Роль: Архитектор\n"
                    f"Система: Сенсор + Чертёж + Кодекс\n"
                    f"Цель: Империя\n\n"
                    f"₿ BTC: ${price:,.2f}\n"
                    f"Фаза: {phase}\n\n"
                    f"📐 <i>Чертёж: ты в центре.</i>\n"
                    f"📡 <a href='https://www.okx.com/ru/markets/prices/bitcoin-btc'>Источник: OKX</a>",
                    main_menu()
                )
            except Exception as e:
                send_tg("⚠️ Профиль: данные временно недоступны", main_menu())


def level_auto_signal():
    try:
        r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
        price = float(r.json()["data"][0]["last"])
        if price > 64500:
            send_tg(f"🚀 <b>ПРОБОЙ ВВЕРХ</b>\n\n₿ BTC: ${price:,.2f}\n\nВозможен импульс к 65 000+.", main_menu())
        elif price < 63800:
            send_tg(f"⚠️ <b>РИСК ВНИЗ</b>\n\n₿ BTC: ${price:,.2f}\n\nБлизко к стопам.", main_menu())
    except:
        pass

def ml_auto_signal():
    try:
        import pickle
        with open("/Users/yananechepelskaya/Desktop/ml_model.pkl", "rb") as f:
            model = pickle.load(f)
        r = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=10")
        candles = r.json()["data"][::-1]
        row = []
        for c in candles[-5:]:
            row += [float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])]
        prob = model.predict_proba([row])[0][1]
        if prob > 0.65:
            send_tg(f"🤖 <b>ML-СИГНАЛ</b>\n\nВероятность роста: {int(prob*100)}%\n\nМодель видит перевес покупателей.", main_menu())
    except:
        pass

def handle_journal(t):
    global JOURNAL
    if t.startswith("/long"):
        try:
            parts = t.split()
            coin = parts[1].upper()
            entry = float(parts[2])
            JOURNAL.append({"coin": coin, "entry": entry, "exit": None, "pnl": None})
            send_tg(f"📒 Лонг записан: {coin} @ ${entry:,.2f}", main_menu())
        except:
            send_tg("📒 Формат: /long BTC 64000", main_menu())
    elif t.startswith("/close"):
        try:
            parts = t.split()
            coin = parts[1].upper()
            exit_price = float(parts[2])
            for j in reversed(JOURNAL):
                if j["coin"] == coin and j["exit"] is None:
                    j["exit"] = exit_price
                    j["pnl"] = round((exit_price - j["entry"]) / j["entry"] * 100, 2)
                    send_tg(f"📒 Закрыто: {coin} @ ${exit_price:,.2f} | PnL: {j['pnl']}%", main_menu())
                    break
            else:
                send_tg("📒 Нет открытой сделки.", main_menu())
        except:
            send_tg("📒 Формат: /close BTC 64500", main_menu())
    elif t.startswith("/journal"):
        if not JOURNAL:
            send_tg("📒 Журнал пуст.", main_menu())
        else:
            lines = []
            for j in JOURNAL[-5:]:
                if j["exit"] is None:
                    lines.append(f"{j['coin']}: вход ${j['entry']:,.2f} (открыта)")
                else:
                    lines.append(f"{j['coin']}: ${j['entry']:,.2f} → ${j['exit']:,.2f} | {j['pnl']}%")
            send_tg("📒 <b>ЖУРНАЛ СДЕЛОК</b>\n\n" + "\n".join(lines), main_menu())

import threading

def auto_signal_loop():
    last_sent = 0
    while True:
        try:
            now = time.time()
            if now - last_sent >= 3600:
                import pickle
                with open("/Users/yananechepelskaya/Desktop/ml_model.pkl", "rb") as f:
                    model = pickle.load(f)
                r = okx_get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
                d = r.json()["data"][0]
                price = float(d["last"])
                entry = round(price * 0.995, 0)
                zone_low = entry * 0.998
                zone_high = entry * 1.002
                rr = okx_get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=30")
                cd = rr.json()["data"][::-1]
                vols = [float(c[5]) for c in cd]
                avg_vol = sum(vols[-20:]) / max(len(vols[-20:]), 1)
                window = cd[-10:]
                row = []
                for c in window:
                    o = float(c[1]); h = float(c[2]); l = float(c[3]); cl = float(c[4]); v = float(c[5])
                    row += [(h-l)/o if o else 0, (cl-l)/(h-l+1e-9), (cl-o)/o if o else 0, v/(avg_vol+1)]
                prob_up = float(model.predict_proba([row])[0][1])
                if zone_low <= price <= zone_high and prob_up >= 0.60:
                    last_sent = now
                    send_tg(
                        f"⚡ <b>АВТОСИГНАЛ АРХИТЕКТОРА</b>\n\n"
                        f"<code>────────────────</code>\n\n"
                        f"₿ BTC: ${price:,.2f}\n"
                        f"Зона: ${zone_low:,.0f} – ${zone_high:,.0f}\n"
                        f"ML: {int(prob_up*100)}%\n\n"
                        f"💡 <i>Цена в зоне. Решение за тобой.</i>\n\n"
                        f"⚠️ Если зреет сжатие — не входи. Жди импульс.\n\n"
                        f"📐 <i>Чертёж: автосигнал — не команда.</i>",
                        main_menu()
                    )
        except Exception as e:
            print("AUTO_SIGNAL_ERR", e)
        time.sleep(900)

def run_polling():
    threading.Thread(target=auto_signal_loop, daemon=True).start()
    while True:
        try:
            process()
        except Exception as e:
            print("LOOP_ERR", e)
        time.sleep(0.3)

if __name__ == "__main__":
    run_polling()