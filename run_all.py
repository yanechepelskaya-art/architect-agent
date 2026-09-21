import subprocess
import time
import sys

processes = [
    subprocess.Popen([sys.executable, "auto_watch.py"]),
    subprocess.Popen([sys.executable, "agent_light.py"]),
    subprocess.Popen([sys.executable, "collect_data.py"]),
]

print("🚀 Запущено 3 процесса: auto_watch, agent_light, collect_data")

try:
    while True:
        time.sleep(30)
        for p in processes:
            code = p.poll()
            if code is not None:
                print(f"⚠️ Процесс умер: {p.args} (код {code})")
except KeyboardInterrupt:
    print("Остановка...")
    for p in processes:
        p.terminate()
