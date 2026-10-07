"""
IIoT device simulator for the blockchain-based zero-trust testbed.

Simulates a factory-floor device (e.g. a vibration sensor on a CNC machine, or a PLC)
that:
  1. Publishes periodic telemetry over MQTT.
  2. Sends discrete "access request" events to the ZT Gateway (gateway.py) whenever it
     needs to reach a protected resource (e.g. write a setpoint to a PLC, pull a firmware
     update). Each request is independently authenticated and authorized -- no session
     persists trust between requests, per the zero-trust design.

Run several instances with different --device-id values to emulate a fleet, and use
--malicious to emulate a compromised/misbehaving device for the security evaluation
(Section 7.1 / attack scenarios in Section 3.3).
"""

import argparse
import json
import random
import time
import uuid

import paho.mqtt.client as mqtt
import requests

def build_client(broker_host, broker_port):
    client = mqtt.Client()
    client.connect(broker_host, broker_port, keepalive=60)
    return client

def publish_telemetry(client, device_id, device_type, malicious):
    reading = {
        "device_id": device_id,
        "device_type": device_type,
        "timestamp": time.time(),
        "value": random.uniform(0.0, 100.0) if not malicious else random.uniform(500, 999),
        "unit": "vibration_mm_s" if device_type == "sensor" else "status",
    }
    client.publish(f"iiot/telemetry/{device_id}", json.dumps(reading))
    return reading

def request_access(gateway_url, device_id, resource, action):
    payload = {"device_id": device_id, "resource": resource, "action": action}
    t0 = time.time()
    try:
        resp = requests.post(f"{gateway_url}/access-request", json=payload, timeout=5)
        latency_ms = (time.time() - t0) * 1000
        return resp.status_code, resp.json(), latency_ms
    except requests.RequestException as e:
        return 599, {"error": str(e)}, (time.time() - t0) * 1000

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device-id", default=str(uuid.uuid4())[:8])
    parser.add_argument("--device-type", default="sensor", choices=["sensor", "plc", "gateway", "hmi"])
    parser.add_argument("--broker-host", default="localhost")
    parser.add_argument("--broker-port", type=int, default=1883)
    parser.add_argument("--gateway-url", default="http://localhost:9000")
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--resource", default="plc-line1/setpoint")
    parser.add_argument("--action", default="write")
    parser.add_argument("--malicious", action="store_true", help="simulate a compromised device (out-of-range values + excessive access attempts)")
    args = parser.parse_args()

    client = build_client(args.broker_host, args.broker_port)
    print(f"[{args.device_id}] simulator started (malicious={args.malicious})")

    while True:
        publish_telemetry(client, args.device_id, args.device_type, args.malicious)

        # request rate spikes for malicious devices to emulate lateral-movement / brute-force behavior
        n_requests = random.randint(5, 15) if args.malicious else 1
        for _ in range(n_requests):
            status, body, latency_ms = request_access(args.gateway_url, args.device_id, args.resource, args.action)
            print(f"[{args.device_id}] access-request -> HTTP {status} | {latency_ms:.1f} ms | {body}")

        time.sleep(args.interval)

if __name__ == "__main__":
    main()
