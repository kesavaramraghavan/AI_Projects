import tiktoken

class Tokenizer:
    def __init__(self, encoding_name="cl100k_base"):
        self.enc = tiktoken.get_encoding(encoding_name)

    def count_tokens(self, text: str) -> int:
        return len(self.enc.encode(text))

    def encode(self, text: str):
        return self.enc.encode(text)

    def decode(self, tokens: list[int]):
        return self.enc.decode(tokens)


def estimate_cost(prompt_tokens: int, completion_tokens: int, prompt_rate=1.5, completion_rate=2.0) -> float:
    prompt_cost = (prompt_tokens / 1_000_000) * prompt_rate
    completion_cost = (completion_tokens / 1_000_000) * completion_rate
    return round(prompt_cost + completion_cost, 6)


def fits_context(prompt_tokens: int, max_completion_tokens: int, context_limit: int = 8000) -> bool:
    return prompt_tokens + max_completion_tokens <= context_limit