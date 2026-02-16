from utils import TokenizerWrapper, load_transcript, split_into_token_chunks

MODEL_CONTEXT_LIMIT = 4000
MAX_COMPLETION_TOKENS = 512
PROMPT_RATE_PER_MILLION = 1.0
COMPLETION_RATE_PER_MILLION = 1.5
SAFETY_MARGIN = 0.8

def estimate_summarization_cost(transcript: str, instructions="You are a meeting summarization assistant."):
    tokenizer = TokenizerWrapper()
    overhead_tokens = tokenizer.count_tokens(instructions) + 50
    available_tokens = int((MODEL_CONTEXT_LIMIT - overhead_tokens - MAX_COMPLETION_TOKENS) * SAFETY_MARGIN)
    if available_tokens <= 0:
        raise ValueError("Context window too small for any transcript tokens.")

    chunks = split_into_token_chunks(transcript, available_tokens, tokenizer)
    num_chunks = len(chunks)
    total_prompt_tokens = (available_tokens + overhead_tokens) * num_chunks
    total_completion_tokens = MAX_COMPLETION_TOKENS * num_chunks
    total_cost = (total_prompt_tokens / 1_000_000) * PROMPT_RATE_PER_MILLION + \
                 (total_completion_tokens / 1_000_000) * COMPLETION_RATE_PER_MILLION

    return {
        "num_chunks": num_chunks,
        "chunk_size_tokens": available_tokens,
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "estimated_total_cost_usd": round(total_cost, 6)
    }

def main():
    transcript = load_transcript("sample_transcript.txt")
    stats = estimate_summarization_cost(transcript)
    print(stats)

if __name__ == "__main__":
    main()
