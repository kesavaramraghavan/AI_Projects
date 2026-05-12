import json
from kafka import KafkaConsumer
from elasticsearch import Elasticsearch
import time

ES_INDEX = "logs-demo"

def ensure_index(es: Elasticsearch):
    if not es.indices.exists(index=ES_INDEX):
        es.indices.create(
            index=ES_INDEX,
            body={
                "mappings": {
                    "properties": {
                        "timestamp": {"type": "date"},
                        "service": {"type": "keyword"},
                        "environment": {"type": "keyword"},
                        "severity": {"type": "keyword"},
                        "message": {"type": "text"},
                        "error_class": {"type": "keyword"},
                        "trace_id": {"type": "keyword"},
                        "deployment_id": {"type": "keyword"}
                    }
                }
            },
        )


def main():
    #es = Elasticsearch("http://elasticsearch:9200")
    def get_es():
        for _ in range(20):
            try:
                es = Elasticsearch("http://elasticsearch:9200")
                if es.ping():
                    return es
            except:
                pass
            time.sleep(2)

        raise Exception("Elasticsearch not ready")
    
    es = get_es()
    ensure_index(es)

    consumer = KafkaConsumer(
        "logs.raw",
        bootstrap_servers="kafka:9092",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )

    print("Kafka consumer started")
    for msg in consumer:
        event = msg.value
        # very basic normalization; you can add masking/parsing here
        es.index(index=ES_INDEX, document=event)


if __name__ == "__main__":
    main()
