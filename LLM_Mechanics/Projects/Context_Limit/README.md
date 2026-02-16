# Project 3: Failure Handling & Context Enforcement

## Overview

This project demonstrates **safe handling of prompts that may exceed context windows**.

Key features:

1. Detect if a prompt fits within the model’s context window
2. Apply **token-aware summarization fallback**
3. Fail fast if even summarized input is too large

---

## Why it matters

- LLMs may **silently truncate** long prompts.
- Users can get incomplete answers without knowing.
- In production, it’s better to **fail loudly** than guess.

---

## What is being used

- **tiktoken** via `TokenizerWrapper`
- Key functions:
  - `count_tokens(text)` → token count
  - `token_summary(text, max_tokens)` → safely truncate large inputs
  - `prepare_prompt_or_fallback(user_prompt, instructions)` → returns a usable prompt or raises an error

---

## How to run

1. Navigate to the folder:

```bash
cd Projects/3_failure_handling_context
```

Run the main script:

```bash
python main.py
```

Run tests:

```bash
pytest -q
```

---

## Expected output

Short input:
`direct 50`

Long input:
`summarized 1024`

Too huge input even after summarization:
`Error: Input too large even after summarization fallback`

- Numbers indicate prompt tokens counted.

Key takeaway
Always enforce context limits and fail fast.
Token-aware summarization ensures your system gracefully handles oversized inputs.
