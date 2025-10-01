import argparse
import asyncio
import json
import random
import socket
import time

def generate_vitals() -> dict:
    heart_rate = int(random.normalvariate(78, 8))
    spo2 = round(random.normalvariate(97.5, 1.0), 1)
    systolic = int(random.normalvariate(118, 10))
    diastolic = int(random.normalvariate(76, 8))
    temperature = round(random.normalvariate(36.8, 0.3), 1)
    respiration = int(random.normalvariate(16, 2))
    return {
        "heart_rate": max(40, min(heart_rate, 180)),
        "spo2": max(80.0, min(spo2, 100.0)),
        "blood_pressure_sys": max(80, min(systolic, 220)),
        "blood_pressure_dia": max(40, min(diastolic, 140)),
        "temperature": max(34.0, min(temperature, 41.0)),
        "respiration_rate": max(8, min(respiration, 40)),
    }

def check_alerts(vitals: dict) -> list[dict]:
    alerts = []
    if random.random() < 0.8 or vitals["temperature"] > 38.0:
        alerts.append({"type": "fever", "message": "Detected fever", "severity": random.choice(["low", "medium", "high"])})
    if random.random() < 0.8 or vitals["spo2"] < 90.0:
        severity = "high" if vitals["spo2"] < 85 else random.choice(["low", "medium", "high"])
        alerts.append({"type": "hypoxia", "message": "Detected hypoxia", "severity": severity})
    if random.random() < 0.8 or vitals["heart_rate"] > 100:
        alerts.append({"type": "tachycardia", "message": "Detected tachycardia", "severity": random.choice(["low", "medium", "high"])})
    if random.random() < 0.8 or vitals["blood_pressure_sys"] > 140 or vitals["blood_pressure_dia"] > 90:
        alerts.append({"type": "hypertension", "message": "Detected hypertension", "severity": random.choice(["low", "medium", "high"])})
    return alerts

async def udp_telemetry_loop(server_ip: str, server_port: int, patient_id: str, interval: float, vitals_state: dict) -> None:
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        while True:
            vitals = generate_vitals()
            vitals_state.clear()
            vitals_state.update(vitals)
            payload = {"patient_id": patient_id, "timestamp": time.time(), "vitals": vitals}
            udp_sock.sendto(json.dumps(payload).encode("utf-8"), (server_ip, server_port))
            await asyncio.sleep(interval)
    finally:
        udp_sock.close()

async def tcp_alerts_loop(server_ip: str, server_port: int, patient_id: str, alert_period: float, vitals_state: dict) -> None:
    reader, writer = await asyncio.open_connection(server_ip, server_port)
    try:
        while True:
            await asyncio.sleep(alert_period)
            if not vitals_state:
                continue
            alerts = check_alerts(vitals_state)
            for alert_info in alerts:
                message = {
                    "patient_id": patient_id,
                    "timestamp": time.time(),
                    "vitals": vitals_state.copy(),
                    **alert_info,
                }
                writer.write((json.dumps(message) + "\n").encode("utf-8"))
                await writer.drain()
                print("TCP alert sent:", message)
    except Exception as e:
        print("TCP send error:", e)
    finally:
        writer.close()
        await writer.wait_closed()




async def main() -> None:
    parser = argparse.ArgumentParser(description="Patient telemetry simulator")
    parser.add_argument("--server", default="127.0.0.1", help="Server IP or hostname")
    parser.add_argument("--udp-port", type=int, default=9999, help="UDP telemetry port")
    parser.add_argument("--tcp-port", type=int, default=9998, help="TCP alerts port")
    parser.add_argument("--patient-id", default="patient-001", help="Patient identifier")
    parser.add_argument("--interval", type=float, default=1.0, help="Telemetry send interval seconds")
    parser.add_argument("--alert-period", type=float, default=15.0, help="Seconds between alerts")
    args = parser.parse_args()

    vitals_state = {}

    await asyncio.gather(
        udp_telemetry_loop(args.server, args.udp_port, args.patient_id, args.interval, vitals_state),
        tcp_alerts_loop(args.server, args.tcp_port, args.patient_id, args.alert_period, vitals_state),
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
