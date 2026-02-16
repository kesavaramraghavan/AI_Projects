# Project 1: Minimal Tokenization + Context + Cost Estimation

## Overview

This project demonstrates the **core mechanics of LLMs**:

1. Text → Tokens
2. Tokens must fit inside a fixed **context window**
3. Each token has a **cost**, so prompt + completion = money

By understanding this, you’ll avoid surprises like truncated prompts or unexpected bills.

---

## Why it matters

- LLMs see **tokens**, not words or characters.
- Prompts exceeding the context window may be **silently truncated**.
- Token-based pricing lets you **predict costs** before sending requests.

---

## What is being used

- **tiktoken**: Converts text to tokens
- Key functions:
  - `count_tokens(text)` → number of tokens
  - `fits_context(prompt_tokens, max_completion_tokens)` → True/False
  - `estimate_cost(prompt_tokens, max_completion_tokens)` → estimated $ cost

---

## How to run

1. Open terminal and navigate to the folder:

```bash
cd examples/1_minimal_token_count
```

2. Run the main example:

```bash
python main.py
```

3. Run tests:

```bash
pytest -q
```

---

## Expected output

Prompt tokens: <some number>
Max completion tokens: 512
Fits context: True
Estimated worst-case cost: $<some float>

i) Numbers will vary based on your input.
ii) Try changing user_question in main.py to see different token counts and costs.

## Key takeaway

Think in tokens, context, and cost, not characters.
This is the foundation for all LLM engineering tasks.
