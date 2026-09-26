def handle_callback(call):
    try:
        data = call.get("data", "")
        if data in ["/status", "status"]:
            phase_icon = "📈" if "Эманация" in last_phase else ("📉" if "Сжатие" in last_phase else "📊")
            reply = f"🏰 <b>ПОРТФЕЛЬ</b>\n{phase_icon} {last_phase}\n<code>──</code>\n"
            for coin, d in PORTFOLIO.items():
                p = get_price(coin)
                if p:
                    pnl = (p - d["entry"]) / d["entry"] * 100
                    reply += f"{'🟢' if pnl>=0 else '🔴'} {coin}: ${p:,.2f} ({pnl:+.2f}%)\n"
            reply += f"💰 Баланс: ${BALANCE:,.2f}"
            send_tg(reply)
        elif data in ["/btc", "btc"]:
            p = get_price("BTC")
            if p: send_tg(f"₿ BTC: ${p:,.2f}")
        elif data in ["/risk", "risk"]:
            reply = "⚠️ <b>РИСК</b>\n"
            for coin, d in PORTFOLIO.items():
                risk = d["amount"] * d["entry"] / BALANCE * 100
                reply += f"{'🔴' if risk>RISK_PERCENT else '🟢'} {coin}: {risk:.1f}%\n"
            reply += f"\n📏 Лимит: {RISK_PERCENT}%"
            send_tg(reply)
        elif data in ["/sensor", "sensor"]:
            p, v = get_market_data_rest("BTC")
            if p and prev_price and prev_vol:
                ch = (p - prev_price) / prev_price * 100
                vol_change = (v - prev_vol) / prev_vol * 100 if prev_vol else 0
                reply = f"🧠 <b>СЕНСОР</b>\nBTC: ${p:,.2f}\nИмпульс: {ch:+.2f}% | Объём: {vol_change:+.1f}%\n\n"
                if ch > 0.5 and v > prev_vol:
                    reply += "🟢 ЛЁГКОСТЬ"
                elif ch > 0.5:
                    reply += "🟡 ТЯЖЕСТЬ (ложный пробой)"
                elif ch < -0.5 and v > prev_vol:
                    reply += "🔴 ТЯЖЕСТЬ"
                elif ch < -0.5:
                    reply += "🟢 ЛЁГКОСТЬ (коррекция)"
                else:
                    reply += "⚪ НЕЙТРАЛЬНО"
                send_tg(reply)
            else:
                send_tg("⏳ Сенсор собирает данные…")
        elif data in ["/advice", "advice"]:
            send_tg("💡 Совет: жди пробой уровня. Без сигнала — без сделки.")
        else:
            send_tg("🔘 Команда не распознана.")
    except Exception as e:
        with open("agent.log", "a") as f:
            f.write(f"CALLBACK_ERR:{e}\n")
