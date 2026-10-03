# 🏰 ARCHITECT AGENT

Telegram-бот для криптоанализа на базе OKX.

**Автор:** Яна
**Дата:** 03.10.2026
**Версия:** 1.0

---

## 🎯 ЧТО ЭТО

Аналитический агент для крипторынка. Собирает данные с OKX, считает фазы, A+, уровни, показывает результат в Telegram.

**Принцип:** правда не требует доказательств. Она просто есть.

---

## 🏗 АРХИТЕКТУРА

Три слоя:
1. Данные — btc_data_v3.csv, training_data_snapshot.csv.
2. Ядро — atr.py, collect_data.py, update_snapshot.py.
3. Витрина — agent_light.py (25+ кнопок).

Поток: OKX → collect_data → btc_data_v3.csv → update_snapshot → training_data_snapshot.csv → agent_light → Telegram.

---

## 📁 ДОКУМЕНТАЦИЯ

- BUTTONS_MAP.md — карта кнопок.
- ARCHITECTURE.md — схема проекта.
- ROADMAP.md — план на 3 месяца.
- METHODOLOGY.md — методология.
- METHODOLOGY_LESSONS.md — 8 уроков.
- PLAN.md — текущий план.
- DAILY_LOG.md — журнал дней.
- experiments.md — гипотезы и проверки.
- SECURITY.md — безопасность.
- PRIVACY.md — приватность.
- DEVICE_SECURITY.md — устройства.
- AUTHORSHIP.md — авторство.
- STRENGTHENING.md — усиление.
- SYSTEM_ANALYSIS.md — сравнение.
- BACKTEST_PLAN.md — бэктест.

---

## 🧿 МЕТОДОЛОГИЯ

Фазы: Сжатие, Импульс, Эманация, Вынос.
A+: 7 слоёв, порог 6/7.
Стиль: swing, R/R ≥ 1:2, стоп всегда.

---

## 🚀 СТАТУС

Сделано:
- OHLC в collect_data.py (22 колонки).
- ATR унифицирован (atr.py).
- Объём в USDT.
- История 12.5 дней.
- Документация.

В работе:
- Токен — ротация.
- Бэктест слоёв.
- Сводка — срез ML/LSTM/Сенсор.

Найдено:
- A+ не даёт edge (бэктест).
- 4 токена в 70+ файлах (отложено).

---

## 🔐 БЕЗОПАСНОСТЬ

См. SECURITY.md, PRIVACY.md, DEVICE_SECURITY.md.

Правила:
- Секреты — только в env.
- API-ключи — без Withdraw, с IP-whitelist.
- 2FA на GitHub.
- Ротация — по расписанию.

---

## 📌 ЗАПУСК

python3 collect_data.py — сбор данных (60 секунд).

python3 update_snapshot.py — snapshot (каждый час, cron).

python3 agent_light.py — агент (Telegram).

---

🏰 Чертёж принят. Работаем по Чертёжу.
