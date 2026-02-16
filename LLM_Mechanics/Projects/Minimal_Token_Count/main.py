from utils import Tokenizer, fits_context, estimate_cost

MODEL_CONTEXT_LIMIT = 8000
MAX_COMPLETION_TOKENS = 512

def example_usage():
    tokenizer = Tokenizer()
    system_prompt = "You are a helpful assistant."
    user_question = "Explain tokenization, context windows, and token-based pricing in simple terms."
    full_prompt = system_prompt + "\n\nUser: " + user_question

    prompt_tokens = tokenizer.count_tokens(full_prompt)
    can_fit = fits_context(prompt_tokens, MAX_COMPLETION_TOKENS, MODEL_CONTEXT_LIMIT)
    est_cost = estimate_cost(prompt_tokens, MAX_COMPLETION_TOKENS)

    print(f"Prompt tokens: {prompt_tokens}")
    print(f"Max completion tokens: {MAX_COMPLETION_TOKENS}")
    print(f"Fits context: {can_fit}")
    print(f"Estimated worst-case cost: ${est_cost}")


if __name__ == "__main__":
    example_usage()
