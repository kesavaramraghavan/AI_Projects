from utils import TokenizerWrapper, token_summary

MODEL_CONTEXT_LIMIT = 4000
MAX_COMPLETION_TOKENS = 512

def prepare_prompt_or_fallback(user_prompt: str, instructions: str):
    tokenizer = TokenizerWrapper()
    full_prompt = instructions + "\n\nUser:\n" + user_prompt
    prompt_tokens = tokenizer.count_tokens(full_prompt)

    if prompt_tokens + MAX_COMPLETION_TOKENS <= MODEL_CONTEXT_LIMIT:
        return {"mode": "direct", "prompt": full_prompt, "prompt_tokens": prompt_tokens}

    # Fallback summarization
    summarized_text = token_summary(user_prompt, tokenizer)
    fallback_prompt = instructions + "\n\nUser (summarized):\n" + summarized_text
    fallback_tokens = tokenizer.count_tokens(fallback_prompt)

    if fallback_tokens + MAX_COMPLETION_TOKENS > MODEL_CONTEXT_LIMIT:
        raise ValueError("Input too large even after summarization fallback.")

    return {"mode": "summarized", "prompt": fallback_prompt, "prompt_tokens": fallback_tokens}

def main():
    instructions = "You are a helpful assistant that answers concisely."
    user_prompt = "Very long text " * 1000
    result = prepare_prompt_or_fallback(user_prompt, instructions)
    print(result["mode"], result["prompt_tokens"])

if __name__ == "__main__":
    main()
