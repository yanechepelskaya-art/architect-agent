# 📅 CHANGELOG — ARCHITECT AGENT

Формат: новое — наверху.

---

## 03.10.2026

**Данные:**
- OHLC в collect_data.py (22 колонки).
- add_features.py — через OHLC.
- Объём в USDT (Статус, Сенсор, Макро).
- fetch_history.py + btc_history.csv (12.5 дней).

**Ядро:**
- ATR унифицирован (atr.py).
- backtest_aplus.py — бэктест.

**Документация:**
- README.md — главный файл.
- _index.md — карта проекта.
- PLAN.md v2.1.
- BUTTONS_MAP, ARCHITECTURE, ROADMAP.
- METHODOLOGY_LESSONS.md — 8 уроков.
- CHANGELOG.md — этот файл.

**Найдено:**
- A+ не даёт edge (бэктест: 0 сигналов, пороги несовместимы).
- 4 токена в 70+ файлах.

---

## 02.10.2026

**Ядро:**
- atr.py — единый ATR (Уайлдер 14).
- update_snapshot.py → atr.py.
- agent_light.py — Рыбка, Часовой → atr.py.

**Безопасность:**
- SECURITY.md v2.0.
- PRIVACY.md (5 слоёв, 3 контура).
- DEVICE_SECURITY.md.
- AUTHORSHIP.md.
- METHODOLOGY.md.

**Документация:**
- STRENGTHENING.md.
- SYSTEM_ANALYSIS.md.
- BACKTEST_PLAN.md.
- DAILY_LOG.md.

**Найдено:**
- ML на синтетике (81 точка).
- Пять ATR → один.

---

## 29.09.2026

**Правка:**
- ML убран из Ликвидаций.

**Проверено (20 кнопок):**
- Энергия, Часовой, Точка входа, Макро.
- Рыбка, Карта, Экран.
- OI, Импульс, A+, HTF, Стакан, Тень.
- Статистика ×2, Сводка.

**Найдено:**
- Фиктивный ATR в A+.
- Статистика Архитектора — литерал.
- Баг единиц объёма.
- Мёртвый Сенсор.

**Документация:**
- Три роли + 10 правил (#56).
- Диагноз проекта (#41).

---

## 25.09.2026

**Старт:**
- btc_data_v3.csv — 18 колонок.
- agent_light.py — 20+ кнопок.
- collect_data.py — сбор.
- update_snapshot.py — snapshot.

---

🏰 Изменения фиксируются с 25.09.2026.
