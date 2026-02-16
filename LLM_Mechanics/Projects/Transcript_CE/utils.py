from pathlib import Path
import tiktoken

def load_transcript(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")

class TokenizerWrapper:
    def __init__(self, encoding_name="cl100k_base"):
        self.enc = tiktoken.get_encoding(encoding_name)

    def count_tokens(self, text: str) -> int:
        return len(self.enc.encode(text))

    def encode(self, text: str):
        return self.enc.encode(text)

    def decode(self, tokens: list[int]):
        return self.enc.decode(tokens)

def split_into_token_chunks(text: str, chunk_prompt_tokens: int, tokenizer: TokenizerWrapper):
    tokens = tokenizer.encode(text)
    chunks = []
    for i in range(0, len(tokens), chunk_prompt_tokens):
        chunks.append(tokenizer.decode(tokens[i:i+chunk_prompt_tokens]))
    return chunks
