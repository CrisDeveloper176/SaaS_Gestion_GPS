import requests
import time
import random

# 🔥 CAMBIA ESTO POR TU URL NGROK
BASE_URL = "https://lola-nonpsychological-emersyn.ngrok-free.dev/api/gps/track/"

DEVICE_ID = "ABCD12"

# Punto base (Concepción)
base_lat = -36.82699
base_lon = -73.04977

print("🚗 Iniciando simulador GPS...\n")

while True:
    # Simulamos pequeño movimiento
    lat = base_lat + random.uniform(-0.002, 0.002)
    lon = base_lon + random.uniform(-0.002, 0.002)
    speed = random.randint(0, 80)

    try:
        response = requests.get(
            BASE_URL,
            params={
                "device": DEVICE_ID,
                "lat": lat,
                "lon": lon,
                "speed": speed,
            },
            timeout=5,
        )

        print(f"📡 Enviado -> Lat:{lat:.6f} Lon:{lon:.6f} Speed:{speed} | Status: {response.status_code}")

    except Exception as e:
        print("❌ Error enviando datos:", e)

    time.sleep(5)