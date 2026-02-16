# Project 2: Transcript Cost Estimator

## Overview

This project simulates a **real business scenario**: summarizing long meeting transcripts using LLMs.

Key goals:

1. Split long text into **token-sized chunks**
2. Respect **context limits**
3. Estimate **total cost** before sending any API calls

---

## Why it matters

- Transcripts often exceed the model’s context window.
- Sending too many tokens can **blow up your costs**.
- Chunking helps **balance cost, latency, and quality**.

---

## What is being used

- **tiktoken** via `TokenizerWrapper`
- Key functions:
  - `load_transcript(path)` → loads transcript text
  - `split_into_token_chunks(text, chunk_prompt_tokens)` → splits transcript
  - `estimate_summarization_cost(transcript)` → returns chunk stats and estimated cost

---

## How to run

1. Navigate to the folder:

```bash
cd Projects/2_business_cost_estimator
```

Ensure sample_transcript.txt exists (multi-paragraph text).

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

```json
{
  "num_chunks": 13,
  "chunk_size_tokens": 2744,
  "total_prompt_tokens": 36426,
  "total_completion_tokens": 6656,
  "estimated_total_cost_usd": 0.04641
}
```

- Numbers vary with transcript length and chunking settings.
- Modify MAX_COMPLETION_TOKENS or transcript length to experiment.

## Key takeaway

In production, splitting and budgeting long inputs is more important than perfect prompts.
Predicting cost avoids wasted money and unnecessary API calls.
