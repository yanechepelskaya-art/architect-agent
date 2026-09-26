from flask import Flask, render_template_string
import requests
from datetime import datetime

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Architect Agent</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body { margin:0; background:#0b0e11; color:#eaeaea; font-family:-apple-system,sans-serif; display:flex; align-items:center; justify-content:center; min-height:100vh; }
.card { background:#11161c; border:1px solid #2b3139; border-radius:20px; padding:32px; width:90%; max-width:460px; box-shadow:0 0 40px rgba(212,175,55,0.06); }
h1 { color:#d4af37; margin:0 0 6px; font-size:24px; }
.sub { color:#888; margin-bottom:24px; }
.row { display:flex; justify-content:space-between; padding:11px 0; border-bottom:1px solid #1e242c; }
.gold { color:#d4af37; font-weight:700; }
.green { color:#2ebd85; font-weight:700; }
.btn { display:block; background:#d4af37; color:#0b0e11; text-align:center; padding:12px; border-radius:12px; margin-top:22px; font-weight:700; text-decoration:none; }
canvas { margin-top:20px; }
</style>
</head>
<body>
<div class="card">
<h1>🏰 Architect Agent</h1>
<div class="sub">Живой портфель · {{ time }}</div>
<div class="row"><span>₿ BTC</span><span class="gold">${{ btc }}</span></div>
<div class="row"><span>🥇 PAXG</span><span class="gold">${{ paxg }}</span></div>
<canvas id="chart" height="120"></canvas>
<a class="btn" href="/">🔄 Обновить</a>
</div>
<script>
const ctx = document.getElementById('chart');
new Chart(ctx, {
  type: 'line',
  data: {
    labels: {{ labels | safe }},
    datasets: [{
      data: {{ prices | safe }},
      borderColor: '#d4af37',
      backgroundColor: 'rgba(212,175,55,0.08)',
      fill: true,
      tension: 0.3,
      pointRadius: 0
    }]
  },
  options: {
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: '#666' } },
      y: { ticks: { color: '#666' } }
    }
  }
});
</script>
</body>
</html>
"""

@app.route("/")
def home():
    try:
        btc = requests.get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT", timeout=10).json()["data"][0]["last"]
    except:
        btc = "—"
    try:
        paxg = requests.get("https://www.okx.com/api/v5/market/ticker?instId=PAXG-USDT", timeout=10).json()["data"][0]["last"]
    except:
        paxg = "—"
    try:
        r = requests.get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=15m&limit=20", timeout=10).json()
        candles = r["data"][::-1]
        labels = [c[0][11:16] for c in candles]
        prices = [float(c[4]) for c in candles]
    except:
        labels = []
        prices = []
    now = datetime.now().strftime("%H:%M")
    return render_template_string(HTML, btc=btc, paxg=paxg, time=now, labels=labels, prices=prices)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
