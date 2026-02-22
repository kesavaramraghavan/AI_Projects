import redis
import json

redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

def get_cache(key: str):
    data = redis_client.get(key)
    return json.loads(data) if data else None

def set_cache(key: str, value: dict, ttl=300):
    redis_client.setex(key, ttl, json.dumps(value))