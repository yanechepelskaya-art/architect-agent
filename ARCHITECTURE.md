# 🏗 АРХИТЕКТУРА ARCHITECT AGENT

Дата: 03.10.2026
Принцип: данные → ядро → витрина.

---

## 📊 СХЕМА ПРОЕКТА

ЛОКАЛЬНО (MacBook): agent_light.py, auto_watch.py, collect_data.py, update_snapshot.py, atr.py.

RENDER (3 сервиса): architect-bot, architect-watch, architect-collect.

GITHUB (приватный): architect-agent.

CRON (локально): update_snapshot.py каждый час.

БИРЖИ: OKX (работает), Binance (451 restricted).

---

## 📡 ПОТОК ДАННЫХ

OKX API → collect_data.py → btc_data_v3.csv (18 колонок).

btc_data_v3.csv → update_snapshot.py → training_data_snapshot.csv (14 колонок).

update_snapshot.py → atr.py → ATR.

training_data_snapshot.csv → agent_light.py → Telegram (25+ кнопок).

---

## 🗂 ТРИ СЛОЯ

### 1. ДАННЫЕ
- btc_data_v3.csv — 18 колонок.
- training_data_snapshot.csv — 14 колонок.
- btc_data_features.csv — из add_features (ATR фиктивный).

### 2. ЯДРО
- atr.py — ATR (Уайлдер 14). ✅
- collect_data.py — сбор 18 колонок. ✅
- update_snapshot.py — snapshot. ✅ → atr.py
- add_features.py — RSI, ATR. ⏳ OHLC.

### 3. ВИТРИНА
- agent_light.py — 25+ кнопок. ⚠️ есть фикции.
- auto_watch.py — слои предупреждения. ⚠️

---

## 🧿 ПРИНЦИПЫ АРХИТЕКТУРЫ

1. Ядро → кнопки. Кнопки берут из модулей.
2. Нет цифры без источника.
3. Один экран — один источник.
4. Единицы едины: USDT, %, $.
5. Прозрачность. Каждый сигнал объясним.

---

## 📌 ЧТО В ДЫРАХ

1. 🔐 Токен в коде — 🔴.
2. ML/LSTM/Сенсор в Сводке — 🟡.
3. 📊 Статистика Архитектора — литерал — 🟡.
4. add_features.py — ATR фиктивный — 🟡.
5. Объём BTC vs USDT — 🟡.
6. Дубли: Макро, Рыбка, Статистика — 🟡.
7. Фазы: 4 словаря — 🟡.
8. Шаблон ±% на 6 экранов — 🟡.

---

🏰 Архитектура зафиксирована.
