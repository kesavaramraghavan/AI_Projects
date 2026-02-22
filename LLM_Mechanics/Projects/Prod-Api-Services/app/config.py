import os

ENCODING_NAME = os.getenv("ENCODING_NAME", "cl100k_base")
MODEL_CONTEXT_LIMIT = int(os.getenv("MODEL_CONTEXT_LIMIT", 16000))

PROMPT_RATE_PER_MILLION = float(os.getenv("PROMPT_RATE_PER_MILLION", 1.0))
COMPLETION_RATE_PER_MILLION = float(os.getenv("COMPLETION_RATE_PER_MILLION", 2.0))

API_KEY = os.getenv("API_KEY", "dev-secret-key")