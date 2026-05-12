import json
import random
import time
from datetime import datetime, timezone

from kafka import KafkaProducer

SERVICES = ["checkout-api", "inventory-service", "payment-gateway"]
SEVERITIES = ["INFO", "WARN", "ERROR"]

SCENARIOS = [
    "normal",
    "inventory-timeout",
    "payment-failure"
]

def create_producer():
    for i in range(20):
        try:
            return KafkaProducer(
                bootstrap_servers="kafka:9092",
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
        except Exception as e:
            print(f"Kafka not ready, retrying... {i}")
            time.sleep(3)
    raise Exception("Kafka not available after retries")

def make_log(service, severity, scenario):
    now = datetime.now(timezone.utc).isoformat()
    if scenario == "inventory-timeout" and service == "checkout-api":
        msg = "timeout calling inventory service"
        error_class = "TimeoutError"
    elif scenario == "payment-failure" and service == "payment-gateway":
        msg = "payment declined by provider"
        error_class = "PaymentDeclined"
    else:
        msg = f"{service} handled request successfully"
        error_class = None

    return {
        "timestamp": now,
        "service": service,
        "environment": "prod",
        "severity": severity,
        "message": msg,
        "error_class": error_class,
        "trace_id": f"trace-{random.randint(1, 1000)}",
        "deployment_id": "deploy_2026_05_11_1400"
    }


def main():
    producer = create_producer()

    print("Log generator started")
    while True:
        scenario = random.choices(SCENARIOS, weights=[0.7, 0.2, 0.1])[0]
        service = random.choice(SERVICES)
        severity = random.choices(SEVERITIES, weights=[0.7, 0.2, 0.1])[0]
        event = make_log(service, severity, scenario)
        producer.send("logs.raw", value=event)
        time.sleep(0.1)  # 10 logs/sec; adjust


if __name__ == "__main__":
    main()
