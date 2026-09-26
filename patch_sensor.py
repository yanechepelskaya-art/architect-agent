import re

with open('agent_light.py', 'r', encoding='utf-8') as f:
    code = f.read()

# ---- НОВАЯ ФУНКЦИЯ ----
new_func = '''
def calculate_pressure_score(df, period=24):
    """
    Вычисляет давление рынка по шкале от -100 до +100.
    Положительное — покупатели, отрицательное — продавцы.
    """
    if df is None or len(df) < period:
        return 0, "недостаточно данных"

    recent = df.tail(period).copy()

    # Изменение цены за период (%)
    price_change_pct = (recent['close'].iloc[-1] - recent['close'].iloc[0]) / recent['close'].iloc[0] * 100

    # Соотношение объёма на росте и падении
    up_volume = recent.loc[recent['close'] > recent['open'], 'volume'].sum()
    down_volume = recent.loc[recent['close'] <= recent['open'], 'volume'].sum()
    total_volume = up_volume + down_volume
    volume_bias = (up_volume - down_volume) / total_volume if total_volume > 0 else 0  # от -1 до 1

    # Ценовое изменение 1% примерно соответствует 30 пунктам
    price_score = max(-100, min(100, price_change_pct * 30))

    # Влияние объёма: до ±30 пунктов
    volume_score = volume_bias * 30

    # Итоговый score
    pressure_score = int(0.7 * price_score + 0.3 * volume_score)

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

    return pressure_score, state
'''

# Вставляем функцию перед первым обычным def, если её ещё нет
if 'def calculate_pressure_score' not in code:
    first_def = re.search(r'\ndef ', code)
    if first_def:
        insert_pos = first_def.start()
        code = code[:insert_pos] + new_func + "\n" + code[insert_pos:]
    else:
        code += "\n" + new_func

# ---- ОБНОВЛЕНИЕ ОБРАБОТЧИКА СЕНСОРА ----
old_sensor_pattern = re.compile(r"(def send_sensor\(.*?\):.*?)(?=\n\ndef |\n\n@|\Z)", re.DOTALL)

new_sensor_func = '''
def send_sensor(chat_id):
    df = get_recent_candles(symbol="BTC-USDT", timeframe="5m", limit=100)
    score, state = calculate_pressure_score(df, period=24)

    if score <= -60:
        emoji = "🔴"
        recommendation = "Продавцы контролируют. Не ловить дно. Ждать разрядки."
    elif score <= -30:
        emoji = "🔴"
        recommendation = "Давление вниз. Входить только по подтверждению."
    elif score < 30:
        emoji = "⚖️"
        recommendation = "Рынок в равновесии. Ждать сигнала."
    elif score < 60:
        emoji = "🟢"
        recommendation = "Покупатели оживают. Искать точку входа по Чертёжу."
    else:
        emoji = "🟢"
        recommendation = "Сильное давление покупателей. Не догонять, но держать лонг."

    text = (
        f"{emoji} СЕНСОР АРХИТЕКТОРА\\n"
        f"────────────────\\n\\n"
        f"Давление: {score} / 100\\n"
        f"Состояние: {state}\\n\\n"
        f"Рекомендация:\\n{recommendation}\\n\\n"
        f"Чертёж: сначала состояние, потом действие."
    )

    bot.send_message(chat_id, text)
'''

if old_sensor_pattern.search(code):
    code = old_sensor_pattern.sub(new_sensor_func, code, count=1)
else:
    code += "\n" + new_sensor_func

with open('agent_light.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("✅ Патч применён: добавлена calculate_pressure_score и обновлён send_sensor")
