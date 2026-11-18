"""Симулятор трьох станцій моніторингу зливових колекторів (Варіант 3)."""
import argparse
import json
import math
import random
import time
from datetime import datetime
import paho.mqtt.client as mqtt

STATIONS = [
    {"id": "lvl-01", "name": "Колектор Центр", "base": 45.0},
    {"id": "lvl-02", "name": "Колектор Низинний", "base": 60.0},
    {"id": "lvl-03", "name": "Колектор Північний", "base": 50.0},
]

PREFIX = "kharkiv/drains"
INTERVAL = 5          # період вимірювання, с
PHI = 0.85            # інерційність ряду AR(1)
SIGMA = 1.2           # шум сенсора рівня, см
GLITCH_P = 0.02       # імовірність збою сенсора (2%)
CYCLE = 600           # тривалість циклу сценарію, с (10 хв)

# Події сценарію (секунди від початку циклу):
# Злива на lvl-02 з 2-ї по 4-ту хв: рівень зростає зі швидкістю 3.0 см/хв (0.25 см за 5 с)
RAIN = ("lvl-02", 60, 300, 30.0)
# Знеструмлення lvl-03 з 6-ї по 8-му хв
OUTAGE = ("lvl-03", 360, 480)


def daily_factor(hour: float) -> float:
    """Добовий профіль стоку (пік ввечері о 20:00)."""
    return 1 + 0.25 * math.cos(2 * math.pi * (hour - 20) / 24)


class Station:
    def __init__(self, cfg, host, port):
        self.id = cfg["id"]
        self.base = cfg["base"]
        self.x = None
        self.mu = None
        self.surge = 0.0
        self.online = False
        self.host, self.port = host, port

        self.c = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"sim-{self.id}"
        )
        self.c.will_set(self.topic("status"), "offline", qos=1, retain=True)
        self.c.on_connect = self.on_connect

    def topic(self, kind):
        return f"{PREFIX}/{self.id}/{kind}"

    def on_connect(self, client, userdata, flags, rc, props):
        client.publish(self.topic("status"), "online", qos=1, retain=True)

    def start(self):
        self.c.connect(self.host, self.port, keepalive=10)
        self.c.loop_start()
        self.online = True

    def power_cut(self):
        self.c.loop_stop()
        self.online = False

    def power_on(self):
        self.c.reconnect()
        self.c.loop_start()
        self.online = True

    def stop(self):
        self.c.publish(self.topic("status"), "offline", qos=1, retain=True).wait_for_publish(2)
        self.c.disconnect()
        self.c.loop_stop()

    def measure(self, hour: float, rain_rate_cm_min: float):
        mu = self.base * daily_factor(hour)
        if self.x is None:
            self.x, self.mu = mu, mu

        eps = random.gauss(0, 1)
        x = mu + PHI * (self.x - self.mu) + SIGMA * eps
        self.x, self.mu = max(x, 5.0), mu

        # Накопичення рівня під час зливи (+rain_rate см/хв) та поступовий спад після неї
        if rain_rate_cm_min > 0:
            self.surge += rain_rate_cm_min * (INTERVAL / 60.0)
        else:
            self.surge = max(0.0, self.surge - 25.0 * (INTERVAL / 60.0))

        h = min(295.0, self.x + self.surge)

        # Імітація збою сенсора (-5 см або 999 см поза діапазоном 0..300)
        if random.random() < GLITCH_P:
            h = random.choice([-5.0, 999.0])

        return {
            "ts": int(time.time() * 1000),
            "h": round(h, 1),
        }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    random.seed(args.seed)
    stations = [Station(s, args.host, args.port) for s in STATIONS]
    for s in stations:
        s.start()

    print(f"Підключено до {args.host}:{args.port}. Ctrl+C зупинити.")
    t0 = time.monotonic()

    try:
        while True:
            phase = (time.monotonic() - t0) % CYCLE
            now = datetime.now()
            hour = now.hour + now.minute / 60.0

            for s in stations:
                cut = (s.id == OUTAGE[0] and OUTAGE[1] <= phase < OUTAGE[2])
                if cut and s.online:
                    s.power_cut()
                    print(f"{now:%H:%M:%S} {s.id} ЗНЕСТРУМЛЕНО")
                elif not cut and not s.online:
                    s.power_on()
                    print(f"{now:%H:%M:%S} {s.id} живлення відновлено")

                if not s.online:
                    continue

                rain_rate = RAIN[3] if (s.id == RAIN[0] and RAIN[1] <= phase < RAIN[2]) else 0.0
                m = s.measure(hour, rain_rate)
                s.c.publish(s.topic("telemetry"), json.dumps(m), qos=1)
                print(f"{now:%H:%M:%S} {s.id} h={m['h']:>6} см")

            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print("Зупинка...")
    finally:
        for s in stations:
            if s.online:
                s.stop()


if __name__ == "__main__":
    main()