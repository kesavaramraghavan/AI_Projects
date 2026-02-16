import tiktoken

class TokenizerWrapper:
    def __init__(self, encoding_name="cl100k_base"):
        self.enc = tiktoken.get_encoding(encoding_name)

    def count_tokens(self, text: str) -> int:
        return len(self.enc.encode(text))

    def encode(self, text: str):
        return self.enc.encode(text)

    def decode(self, tokens: list[int]):
        return self.enc.decode(tokens)

def token_summary(text: str, tokenizer: TokenizerWrapper, max_tokens: int = 200) -> str:
    tokens = tokenizer.encode(text)
    if len(tokens) <= max_tokens:
        return text
    return tokenizer.decode(tokens[:max_tokens]) + " ... [TRUNCATED SUMMARY]"
