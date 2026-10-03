# 📌 ИНДЕКС ФАЙЛОВ — ARCHITECT AGENT

Дата: 03.10.2026
Назначение: карта проекта. Где что лежит.

---

## 📁 ДОКУМЕНТАЦИЯ

| Файл | Что |
|------|-----|
| README.md | Главный файл. Что это, запуск. |
| _index.md | Этот файл. Карта проекта. |
| BUTTONS_MAP.md | Карта кнопок: реальные / смешанные / фикции. |
| ARCHITECTURE.md | Схема: данные → ядро → витрина. |
| ROADMAP.md | План на 3 месяца. |
| PLAN.md | Текущий план (источник правды). |
| plan_next.md | Архив. |
| METHODOLOGY.md | Методология: фазы, A+, правила. |
| METHODOLOGY_LESSONS.md | 8 уроков. |
| DAILY_LOG.md | Журнал дней. |
| experiments.md | Гипотезы и проверки (#1–#96). |
| STRENGTHENING.md | 7 направлений усиления. |
| SYSTEM_ANALYSIS.md | Сравнение с другими системами. |
| BACKTEST_PLAN.md | План бэктеста. |

---

## 🔐 БЕЗОПАСНОСТЬ

| Файл | Что |
|------|-----|
| SECURITY.md | Регламент безопасности агента. |
| PRIVACY.md | Приватность (5 слоёв, 3 контура). |
| DEVICE_SECURITY.md | Безопасность устройств. |
| AUTHORSHIP.md | Авторство. |

---

## 🧠 КОД — ЯДРО

| Файл | Что |
|------|-----|
| atr.py | ATR (Уайлдер 14, OKX). |
| collect_data.py | Сбор 22 колонок (OHLC). |
| update_snapshot.py | Snapshot (14 колонок). |
| fetch_history.py | Загрузка истории с OKX. |
| add_features.py | RSI, ATR, features. |
| backtest_aplus.py | Бэктест A+. |

---

## 🤖 КОД — ВИТРИНА

| Файл | Что |
|------|-----|
| agent_light.py | 25+ кнопок Telegram. |
| auto_watch.py | Слои предупреждения. |

---

## 📊 ДАННЫЕ

| Файл | Что |
|------|-----|
| btc_data_v3.csv | Свежие данные (22 колонки). |
| training_data_snapshot.csv | Snapshot для A+. |
| btc_history.csv | История (12.5 дней). |
| backtest_result.csv | Результат бэктеста. |

---

## 🔧 ИНФРАСТРУКТУРА

- Git: приватный репо.
- Render: 3 сервиса (bot, watch, collect).
- Cron: update_snapshot (час), collect (@reboot).
- Telegram: @BotFather.

---

## 📌 ПРАВИЛА

- Чертёж: 30 правил.
- Три роли (#56): Архитектор, Тестировщик, Ревьюер.
- 10 правил построения (#56).
- Единицы: USDT, %, $.
- Фазы: Сжатие, Импульс, Эманация, Вынос.

---

## 🎯 БЫСТРЫЙ СТАРТ

1. **Понять проект** → README.md → ARCHITECTURE.md.
2. **Понять методологию** → METHODOLOGY.md → METHODOLOGY_LESSONS.md.
3. **Понять план** → PLAN.md → ROADMAP.md.
4. **Понять историю** → DAILY_LOG.md → experiments.md.
5. **Понять кнопки** → BUTTONS_MAP.md.

---

🏰 Индекс зафиксирован. Добро пожаловать в проект.
