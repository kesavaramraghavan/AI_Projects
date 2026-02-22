import time
import tiktoken
from functools import lru_cache
from .config import (
    ENCODING_NAME,
    MODEL_CONTEXT_LIMIT,
    PROMPT_RATE_PER_MILLION,
    COMPLETION_RATE_PER_MILLION,
)
from .cache import get_cache, set_cache

# In-memory per-user cost tracking (for demo; replace with Redis/db in prod)
USER_BUDGET = {}

@lru_cache(maxsize=1)
def get_encoding():
    """Get tokenizer encoding, cached for performance."""
    return tiktoken.get_encoding(ENCODING_NAME)

def count_tokens(text: str) -> int:
    """Count tokens in a string using the configured encoding."""
    enc = get_encoding()
    return len(enc.encode(text))

def estimate_cost(prompt_tokens: int, max_completion_tokens: int) -> float:
    """Compute worst-case estimated cost in USD."""
    prompt_cost = (prompt_tokens / 1_000_000) * PROMPT_RATE_PER_MILLION
    completion_cost = (max_completion_tokens / 1_000_000) * COMPLETION_RATE_PER_MILLION
    return round(prompt_cost + completion_cost, 6)

def process_estimate(prompt: str, max_completion_tokens: int, user_id: str = "anonymous") -> dict:
    """
    Compute token count, context fit, and cost for a given prompt.
    Uses caching to speed up repeated requests.
    Tracks per-user budget in memory.
    """
    start = time.perf_counter()
    cache_key = f"{user_id}:{prompt}:{max_completion_tokens}"

    # Check cache first
    cached = get_cache(cache_key)
    if cached:
        return cached

    # Core computation
    prompt_tokens = count_tokens(prompt)
    fits = (prompt_tokens + max_completion_tokens) <= MODEL_CONTEXT_LIMIT
    total_cost = estimate_cost(prompt_tokens, max_completion_tokens)

    # Track user budget
    USER_BUDGET[user_id] = USER_BUDGET.get(user_id, 0) + total_cost

    duration_ms = (time.perf_counter() - start) * 1000

    result = {
        "prompt_tokens": prompt_tokens,
        "fits_context": fits,
        "estimated_max_cost_usd": total_cost,
        "duration_ms": round(duration_ms, 2),
    }

    # Store in cache
    set_cache(cache_key, result)
    return result