# File: api/app/config.py
import os

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "your-api-key")
API_KEY = os.getenv("API_KEY", "dev-secret-key")

ENCODING_NAME = "cl100k_base"
MODEL_CONTEXT_LIMIT = 16000
PROMPT_RATE_PER_MILLION = 1.0
COMPLETION_RATE_PER_MILLION = 2.0

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

USER_BUDGET_THRESHOLD = 5.0  # USD per user