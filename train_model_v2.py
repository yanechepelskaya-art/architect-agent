import csv
import pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

X = []
y = []

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

with open("btc_data_features.csv", "r") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

prev_close = None
for i, row in enumerate(rows):
    try:
        price = float(row["price"])
        phase = detect_phase(prev_close, price) if prev_close else "flat"
        prev_close = price

        if phase == "flat":
            continue

        features = [
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
        ]
        X.append(features)
        y.append(phase)
    except Exception:
        continue

print(f"Собрано {len(X)} примеров")

if len(X) < 100:
    print("❌ Мало данных")
else:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    print(f"✅ Точность: {acc*100:.2f}%")
    print(f"Классы: {set(y)}")

    with open("phase_model_v2.pkl", "wb") as f:
        pickle.dump(model, f)
    print("✅ Модель сохранена: phase_model_v2.pkl")
