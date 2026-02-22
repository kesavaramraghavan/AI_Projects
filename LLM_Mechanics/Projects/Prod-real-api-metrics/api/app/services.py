from functools import lru_cache
from .config import (
    ENCODING_NAME,
    MODEL_CONTEXT_LIMIT,
    PROMPT_RATE_PER_MILLION,
    COMPLETION_RATE_PER_MILLION,
    OPENROUTER_API_KEY
)
from .cache import get_cache, set_cache
from openai import OpenAI
import tiktoken

USER_BUDGET = {}

@lru_cache(maxsize=1)
def get_encoding():
    return tiktoken.get_encoding(ENCODING_NAME)

def count_tokens(text: str) -> int:
    return len(get_encoding().encode(text))

def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    return round(
        (prompt_tokens / 1_000_000) * PROMPT_RATE_PER_MILLION +
        (completion_tokens / 1_000_000) * COMPLETION_RATE_PER_MILLION,
        6
    )

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)

def get_model_response(prompt: str, max_tokens: int) -> str:
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-5.2",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"[ERROR CALLING MODEL]: {str(e)}"

def process_estimate(prompt: str, max_completion_tokens: int, user_id: str):
    cache_key = f"{user_id}:{prompt}:{max_completion_tokens}"
    cached = get_cache(cache_key)
    if cached:
        return cached

    model_response = get_model_response(prompt, max_completion_tokens)
    prompt_tokens = count_tokens(prompt)
    completion_tokens = count_tokens(model_response)
    fits_context = (prompt_tokens + completion_tokens) <= MODEL_CONTEXT_LIMIT
    total_cost = estimate_cost(prompt_tokens, completion_tokens)
    USER_BUDGET[user_id] = USER_BUDGET.get(user_id, 0) + total_cost

    result = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "fits_context": fits_context,
        "estimated_max_cost_usd": total_cost,
        "model_response": model_response
    }

    set_cache(cache_key, result)
    return result