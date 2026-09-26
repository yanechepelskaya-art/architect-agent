import csv
import pickle
from sklearn.metrics import accuracy_score

def detect_phase(prev_close, close):
    if prev_close == 0:
        return "flat"
    chg = (close - prev_close) / prev_close * 100
    if abs(chg) < 0.3:
        return "compression"
    elif 0.3 <= abs(chg) < 1.5:
        return "impulse"
    elif chg >= 1.5:
        return "emanation"
    elif chg <= -1.5:
        return "flush"
    return "flat"

# Загружаем модели
with open("phase_model.pkl", "rb") as f:
    model_v1 = pickle.load(f)
with open("phase_model_v2.pkl", "rb") as f:
    model_v2 = pickle.load(f)

# Загружаем данные
with open("btc_data_features.csv", "r") as f:
    rows = list(csv.DictReader(f))

# Берём последние 200 строк
rows = rows[-200:]

X_old = []  # для v1 (7 фич)
X_new = []  # для v2 (10 фич)
y_true = []

prev_close = None
for i, row in enumerate(rows):
    try:
        price = float(row["price"])
        phase = detect_phase(prev_close, price) if prev_close else "flat"
        prev_close = price

        if phase == "flat":
            continue

        # v1: 7 фич
        X_old.append([
            float(row["price"]),
            float(row["vol24h"]),
            float(row["oi"]),
            float(row["funding"]),
            float(row["delta"]),
            0,  # change
            0,  # vol_change
        ])

        # v2: 10 фич
        X_new.append([
            float(row["price"]),
            float(row["vol24h"]),
            float(row["oi"]),
            float(row["funding"]),
            float(row["delta"]),
            float(row["atr"]),
            float(row["rsi"]),
            float(row["hour"]),
            float(row["price_change_5"]),
            float(row["oi_change_5"]),
        ])

        y_true.append(phase)
    except Exception:
        continue

print(f"Тестовых примеров: {len(y_true)}")

if len(y_true) > 0:
    y_pred_v1 = model_v1.predict(X_old)
    y_pred_v2 = model_v2.predict(X_new)

    acc_v1 = accuracy_score(y_true, y_pred_v1)
    acc_v2 = accuracy_score(y_true, y_pred_v2)

    print(f"📊 v1 точность: {acc_v1*100:.2f}%")
    print(f"📊 v2 точность: {acc_v2*100:.2f}%")

    if acc_v1 > acc_v2:
        print("🏆 Победитель: v1")
    elif acc_v2 > acc_v1:
        print("🏆 Победитель: v2")
    else:
        print("⚖️ Ничья")
