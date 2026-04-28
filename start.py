import subprocess
import sys
import os
import webbrowser
import time

# Pfade
ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.join(ROOT, "frontend")

print("🚀 Mercado startet...")

# Backend starten
backend = subprocess.Popen(
    ["uvicorn", "api.main:app", "--reload"],
    cwd=ROOT
)

# Frontend starten
frontend = subprocess.Popen(
    [sys.executable, "-m", "http.server", "8001"],
    cwd=FRONTEND
)

print("✅ Backend läuft auf http://127.0.0.1:8000")
print("✅ Frontend läuft auf http://127.0.0.1:8001")

# Browser öffnen
time.sleep(2)
webbrowser.open("http://127.0.0.1:8001")

print("\n⛔ CTRL+C zum Beenden\n")

try:
    backend.wait()
except KeyboardInterrupt:
    print("\n🛑 Stopping...")
    backend.terminate()
    frontend.terminate()