import requests
import time
import json
import sqlite3
from datetime import datetime, timedelta
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
import ccxt

API_KEY = "4197cf46-f0cd-475b-b0dc-31e42763c77c"
SECRET_KEY = "A088B1B1307E659FC85A8FF2A55A5899"
PASSPHRASE = "Kukuruza2026)"

TOKEN = "8900618226:AAE1o5o_xH1eSG4jwz7vCksardv_7SISy8c"
CHAT_ID = "870512243"
CHANNEL_ID = "-1003920623687"

PORTFOLIO = {
    "BTC": {"entry": 61900, "stop": 59500, "target": 68000, "amount": 0.01},
    "ETH": {"entry": 1550, "stop": 1450, "target": 2000, "amount": 0.1},
    "SOL": {"entry": 55, "stop": 48, "target": 82, "amount": 1.0},
    "WLD": {"entry": 0.60, "stop": 0.50, "target": 0.70, "amount": 100},
    "DOGE": {"entry": 0.069, "stop": 0.060, "target": 0.085, "amount": 1000},
    "XRP": {"entry": 1.05, "stop": 0.90, "target": 1.30, "amount": 100},
    "SUI": {"entry": 0.68, "stop": 0.55, "target": 0.90, "amount": 50},
    "RENDER": {"entry": 1.42, "stop": 1.20, "target": 1.80, "amount": 50}
}

BALANCE = 759.89
RISK_PERCENT = 2.0
TRAILING_PERCENT = 3.0
prev_price = None
prev_vol = None
last_phase = "Неизвестно"
last_update_id = 0

PAPER_BALANCE = 10000.0
PAPER_POSITION = None

def init_paper_db():
    conn = sqlite3.connect("paper_trades.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        coin TEXT,
        action TEXT,
        price REAL,
        amount REAL,
        pnl REAL,
        reason TEXT
    )""")
    conn.commit()
    conn.close()

def log_paper_trade(coin, action, price, amount, pnl=0, reason=""):
    conn = sqlite3.connect("paper_trades.db")
    c = conn.cursor()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO trades (timestamp, coin, action, price, amount, pnl, reason) VALUES (?,?,?,?,?,?,?)",
              (ts, coin, action, price, amount, pnl, reason))
    conn.commit()
    conn.close()

def send_voice(text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendVoice"
        import tempfile, os
        from subprocess import run
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(text)
            f.flush()
            tmp_path = f.name
        audio_path = tmp_path + ".m4a"
        run(["say", "-o", audio_path, "--data-format=alac", text], capture_output=True, timeout=10)
        with open(audio_path, 'rb') as af:
            requests.post(url, params={"chat_id": CHAT_ID}, files={"voice": af}, timeout=15)
        os.remove(tmp_path)
        os.remove(audio_path)
    except:
        pass

def send_tg(text, reply_markup=None, to_channel=False):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        target = CHANNEL_ID if to_channel else CHAT_ID
        params = {"chat_id": target, "text": text, "parse_mode": "HTML"}
        if reply_markup and not to_channel:
            params["reply_markup"] = json.dumps(reply_markup)
        requests.get(url, params=params, timeout=10)
    except:
        pass

def get_market_data(symbol="BTC"):
    try:
        url = f"https://www.okx.com/api/v5/market/ticker?instId={symbol}-USDT"
        r = requests.get(url, timeout=5)
        d = r.json()
        return float(d["data"][0]["last"]), float(d["data"][0]["vol24h"])
    except:
        return None, None

def get_price(symbol):
    p, _ = get_market_data(symbol)
    return p

def export_to_excel():
    try:
        conn = sqlite3.connect("paper_trades.db")
        c = conn.cursor()
        c.execute("SELECT * FROM trades ORDER BY id DESC")
        rows = c.fetchall()
        conn.close()
        wb = Workbook()
        ws = wb.active
        ws.title = "История сделок"
        headers = ["Дата", "Монета", "Действие", "Цена", "Объём", "PnL", "Причина"]
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")
        for i, r in enumerate(rows, 2):
            ws.cell(row=i, column=1, value=r[1])
            ws.cell(row=i, column=2, value=r[2])
            ws.cell(row=i, column=3, value=r[3])
            ws.cell(row=i, column=4, value=f"${r[4]:,.2f}")
            ws.cell(row=i, column=5, value=f"{r[5]:.6f}")
            c = ws.cell(row=i, column=6, value=f"{r[6]:+,.2f}" if r[6] else "$0.00")
            c.font = Font(color="16A34A" if r[6] and r[6] >= 0 else "DC2626")
            ws.cell(row=i, column=7, value=r[7])
        fn = f"trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        wb.save(f"/Users/yananechepelskaya/Desktop/{fn}")
        send_tg(f"📊 Экспорт: {fn}")
    except Exception as e:
        send_tg(f"Ошибка: {e}")

def predict():
    p, v = get_market_data("BTC")
    if not p or not prev_price:
        send_tg("⏳ Прогноз: жду данные")
        return
    ch = (p - prev_price) / prev_price * 100
    reply = f"🔮 <b>Прогноз BTC</b>\nЦена: ${p:,.2f}\n"
    if ch > 0.5 and v and v > prev_vol:
        reply += "🟢 Лёгкость — рост к $64,500"
    elif ch < -0.5 and v and v > prev_vol:
        reply += "🔴 Тяжесть — снижение к $63,000"
    elif abs(ch) <= 0.5:
        reply += "⚪ Нейтрально — боковик"
    else:
        reply += "⚠️ Смешанный сигнал"
    send_tg(reply)

def backtest():
    send_tg("⏳ <b>Backtest запущен...</b>\nАнализирую последние 30 дней BTC. Ждите 1–2 минуты.")
    try:
        exchange = ccxt.okx()
        since = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
        ohlcv = exchange.fetch_ohlcv("BTC/USDT", "1d", since=since)

        balance = 10000.0
        position = None
        trades = 0
        wins = 0

        for candle in ohlcv:
            close_price = candle[4]
            if position is None:
                if close_price < 64000:
                    position = {"entry": close_price, "stop": close_price * 0.98, "target": close_price * 1.03}
            else:
                if close_price <= position["stop"]:
                    pnl = (close_price - position["entry"]) / position["entry"] * balance * 0.02
                    balance += pnl
                    trades += 1
                    if pnl > 0: wins += 1
                    position = None
                elif close_price >= position["target"]:
                    pnl = (close_price - position["entry"]) / position["entry"] * balance * 0.02
                    balance += pnl
                    trades += 1
                    if pnl > 0: wins += 1
                    position = None

        winrate = (wins / trades * 100) if trades > 0 else 0
        profit = balance - 10000.0

        reply = f"<b>📊 BACKTEST BTC (30 дней)</b>\n<code>──────────────────</code>\n\n"
        reply += f"💰 Стартовый депозит: <b>$10,000</b>\n"
        reply += f"💰 Итоговый баланс: <b>${balance:,.2f}</b>\n"
        reply += f"📈 Прибыль: <b>${profit:+,.2f}</b> ({profit/10000*100:+.2f}%)\n"
        reply += f"📋 Всего сделок: <b>{trades}</b>\n"
        reply += f"🎯 Винрейт: <b>{winrate:.1f}%</b>"
        send_tg(reply)
    except Exception as e:
        send_tg(f"Ошибка backtest: {e}")

def daily_channel_summary():
    phase_icon = "📈" if "Эманация" in last_phase else ("📉" if "Сжатие" in last_phase else "📊")
    summary = f"<b>🏰 АРХИТЕКТОР: ЕЖЕДНЕВНАЯ СВОДКА</b>\n📅 {datetime.now().strftime('%d.%m.%Y')}\n{phase_icon} {last_phase}\n<code>──</code>\n\n"
    for coin, d in PORTFOLIO.items():
        p = get_price(coin)
        if p:
            pnl = (p - d["entry"]) / d["entry"] * 100
            summary += f"{'🟢' if pnl>=0 else '🔴'} {coin}: ${p:,.2f} ({pnl:+.2f}%)\n"
    summary += f"\n💰 Баланс: ${BALANCE:,.2f}"
    send_tg(summary, to_channel=True)

def process_updates():
    global last_update_id, last_phase
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        r = requests.get(url, params={"offset": last_update_id + 1, "timeout": 5}, timeout=10).json()
        for upd in r.get("result", []):
            last_update_id = upd["update_id"]
            t = upd.get("message", {}).get("text", "")
            if t in ["/status", "📊 Статус"]:
                phase_icon = "📈" if "Эманация" in last_phase else ("📉" if "Сжатие" in last_phase else "📊")
                reply = f"<b>🏰 Портфель</b>\n{phase_icon} {last_phase}\n<code>──</code>\n"
                for coin, d in PORTFOLIO.items():
                    p = get_price(coin)
                    if p:
                        pnl = (p - d["entry"]) / d["entry"] * 100
                        reply += f"{'🟢' if pnl>=0 else '🔴'} {coin}: ${p:,.2f} ({pnl:+.2f}%)\n"
                reply += f"💰 Баланс: ${BALANCE:,.2f}"
                send_tg(reply)
            elif t in ["/btc", "₿ BTC"]:
                p = get_price("BTC")
                if p: send_tg(f"₿ BTC: ${p:,.2f}")
            elif t in ["/risk", "⚠️ Риск"]:
                reply = "<b>⚠️ Риск</b>\n"
                for coin, d in PORTFOLIO.items():
                    risk = d["amount"] * d["entry"] / BALANCE * 100
                    reply += f"{'🔴' if risk>RISK_PERCENT else '🟢'} {coin}: {risk:.1f}%\n"
                send_tg(reply)
            elif t in ["/sensor", "🧠 Сенсор"]:
                p, v = get_market_data("BTC")
                if p and prev_price:
                    ch = (p - prev_price) / prev_price * 100
                    q = "🟢 Лёгкость" if ch > 0.5 else ("🔴 Тяжесть" if ch < -0.5 else "⚪ Нейтрально")
                    send_tg(f"<b>🧠 Сенсор BTC:</b> {q}\nЦена: ${p:,.2f}")
                else:
                    send_tg("⏳ Сенсор: жду данные")
            elif t in ["/paper", "📝 Paper"]:
                p = get_price("BTC")
                if PAPER_POSITION and p:
                    pnl = (p - PAPER_POSITION["entry"]) / PAPER_POSITION["entry"] * 100
                    send_tg(f"<b>📝 Paper</b>\nБаланс: ${PAPER_BALANCE:,.2f}\nBTC: вход ${PAPER_POSITION['entry']:,.2f}, тек. ${p:,.2f}, PnL {pnl:+.2f}%")
                else:
                    send_tg(f"<b>📝 Paper</b>\nБаланс: ${PAPER_BALANCE:,.2f}\nНет позиций")
            elif t in ["/history", "📋 История"]:
                conn = sqlite3.connect("paper_trades.db")
                c = conn.cursor()
                c.execute("SELECT * FROM trades ORDER BY id DESC LIMIT 10")
                rows = c.fetchall()
                conn.close()
                reply = "<b>📋 История</b>\n" + "\n".join([f"{'🟢' if r[6] and r[6]>=0 else '🔴'} {r[1]} {r[3]} ${r[4]:,.2f} PnL:{r[6]:+,.2f}" for r in rows]) if rows else "Пусто"
                send_tg(reply)
            elif t in ["/export", "📊 Экспорт"]:
                export_to_excel()
            elif t in ["/predict", "🔮 Прогноз"]:
                predict()
            elif t in ["/backtest", "📈 Backtest"]:
                backtest()
    except:
        pass

def update_trailing_stop():
    for coin, d in PORTFOLIO.items():
        p = get_price(coin)
        if p:
            pnl = (p - d["entry"]) / d["entry"] * 100
            if pnl >= TRAILING_PERCENT:
                new_stop = p * 0.98
                if new_stop > d["stop"]:
                    d["stop"] = round(new_stop, 2)
                    send_voice(f"Трейлинг стоп {coin} обновлён")
                    send_tg(f"🔄 Трейлинг-стоп {coin}: ${d['stop']:,.2f}")

def check_sharp_move():
    global prev_price
    p, v = get_market_data("BTC")
    if p and prev_price:
        ch = (p - prev_price) / prev_price * 100
        if abs(ch) >= 1.0:
            direction = "Рост" if ch > 0 else "Падение"
            send_voice(f"Резкое движение биткоина! {direction} на {abs(ch):.1f} процентов")
            send_tg(f"⚡ Резкое движение BTC: {direction} на {abs(ch):.2f}%, цена ${p:,.2f}")

def paper_trade_logic():
    global PAPER_BALANCE, PAPER_POSITION
    p, v = get_market_data("BTC")
    if not p:
        return
    if PAPER_POSITION is None:
        if p < 64000:
            amount = PAPER_BALANCE * 0.02 / p
            PAPER_POSITION = {"entry": p, "amount": amount, "stop": p * 0.98, "target": p * 1.03}
            log_paper_trade("BTC", "BUY", p, amount, reason="Сигнал Сенсора")
            send_tg(f"📝 Paper BUY BTC @ ${p:,.2f}")
    else:
        if p <= PAPER_POSITION["stop"]:
            pnl = PAPER_POSITION["amount"] * (p - PAPER_POSITION["entry"])
            PAPER_BALANCE += pnl
            log_paper_trade("BTC", "SELL", p, PAPER_POSITION["amount"], pnl, "Стоп-лосс")
            send_voice(f"Paper стоп лосс")
            send_tg(f"📝 Paper SELL BTC @ ${p:,.2f} (стоп-лосс), PnL: ${pnl:+,.2f}")
            PAPER_POSITION = None
        elif p >= PAPER_POSITION["target"]:
            pnl = PAPER_POSITION["amount"] * (p - PAPER_POSITION["entry"])
            PAPER_BALANCE += pnl
            log_paper_trade("BTC", "SELL", p, PAPER_POSITION["amount"], pnl, "Тейк-профит")
            send_voice(f"Paper тейк профит")
            send_tg(f"📝 Paper SELL BTC @ ${p:,.2f} (тейк-профит), PnL: ${pnl:+,.2f}")
            PAPER_POSITION = None
        else:
            new_stop = p * 0.98
            if new_stop > PAPER_POSITION["stop"]:
                PAPER_POSITION["stop"] = round(new_stop, 2)

keyboard = {"keyboard": [["📊 Статус", "🧠 Сенсор"], ["⚠️ Риск", "₿ BTC"], ["📝 Paper", "📋 История"], ["📊 Экспорт", "🔮 Прогноз"], ["📈 Backtest", "📊 Экспорт"]], "resize_keyboard": True}
print("Архитектор: агент с backtest запущен")
init_paper_db()
send_tg("👋 Агент онлайн. Backtest готов.", keyboard)

p, v = get_market_data("BTC")
if p:
    prev_price = p
    prev_vol = v

last_check = time.time()
last_summary = time.time()
last_trailing = time.time()
last_paper = time.time()
last_sharp_check = time.time()
last_daily = time.time()

while True:
    process_updates()
    time.sleep(1)
    now = time.time()
    if now - last_check >= 300:
        for coin, d in PORTFOLIO.items():
            p = get_price(coin)
            if p:
                if p >= d["target"]:
                    send_voice(f"Тейк профит {coin}")
                    send_tg(f"🎯 ТЕЙК-ПРОФИТ {coin}! ${p:,.2f}")
                elif p <= d["stop"]:
                    send_voice(f"Стоп лосс {coin}")
                    send_tg(f"🛑 СТОП-ЛОСС {coin}! ${p:,.2f}")
        p, v = get_market_data("BTC")
        if p and prev_price:
            if p > prev_price:
                last_phase = "📈 Эманация"
            elif p < prev_price:
                last_phase = "📉 Сжатие"
            else:
                last_phase = "📊 Боковик"
        if p:
            prev_price = p
            prev_vol = v
        last_check = now
    if now - last_sharp_check >= 300:
        check_sharp_move()
        last_sharp_check = now
    if now - last_trailing >= 600:
        update_trailing_stop()
        last_trailing = now
    if now - last_paper >= 300:
        paper_trade_logic()
        last_paper = now
    if now - last_daily >= 86400:
        daily_channel_summary()
        last_daily = now
    if now - last_summary >= 3600:
        summary = f"<b>📊 Сводка</b>\nФаза: {last_phase}\n"
        for coin, d in PORTFOLIO.items():
            p = get_price(coin)
            if p:
                pnl = (p - d["entry"]) / d["entry"] * 100
                summary += f"{'🟢' if pnl>=0 else '🔴'} {coin}: ${p:,.2f} ({pnl:+.2f}%)\n"
        summary += f"💰 Баланс: ${BALANCE:,.2f}"
        send_tg(summary)
        last_summary = now