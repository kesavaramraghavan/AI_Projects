# Generation Controls

Production-ready generation controls for LLM decoding: validate configs, bound output length, reduce repetition, and stop reliably.

## Scope (roadmap-aligned)

This repo implements the **Generation Controls** items from the AI Agents roadmap PDF under **LLM Fundamentals**:

- Temperature
- Top-p
- Frequency penalty
- Presence penalty
- Stopping criteria
- Max length (max tokens)

Top-k is intentionally out of scope because it is not listed in the PDF’s Generation Controls line.

## Features

- Input validation for generation parameters
- Presets for common modes (deterministic, creative, extraction)
- Repetition controls (presence/frequency penalties)
- Sampling controls (temperature/top-p)
- Stopping controls (stop sequences, EOS, max length)
- FastAPI service (`POST /generate`)
- Dockerfile + minimal Kubernetes manifest
- Unit tests + API integration test
- Observability hooks (structured logs; metric points)

## Repository layout

```text
generation-controls/
- requirements.txt
- .env
- pyproject.toml
- src/
  - gen_controls/
    - __init__.py
    - client.py
    - config.py
    - service.py
    - presets.py
    - observability.py
    - validation.py
- examples/
  - 1_minimal_demo.py
  - 2_business_json_extraction.py
  - 3_creative_generation.py
- api/
  - app.py
  - Dockerfile
  - k8s.yaml
  - test_app.py
- tests/
  - test_service.py
```

## Quickstart

### Create venv and install

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run tests

```bash
pytest -q
```

### Run examples

```bash
python examples/1_minimal_demo.py
python examples/2_business_json_extraction.py
python examples/3_creative_generation.py
```

## Parameter cheatsheet

| Parameter                       | Purpose                            | Typical use                                               | Common failure mode                                |
| ------------------------------- | ---------------------------------- | --------------------------------------------------------- | -------------------------------------------------- |
| `temperature`                   | Randomness of sampling             | 0.0–0.3 for extraction/tool calls; 0.7–1.0 for creativity | Too high: unstable/incoherent                      |
| `top_p`                         | Nucleus sampling cutoff            | 0.8–0.95 for conservative diversity                       | Too low: bland; too high: drift                    |
| `max_tokens` / `max_new_tokens` | Hard cap on output length          | Always set in production                                  | Too low: truncation; too high: cost/latency spikes |
| `frequency_penalty`             | Penalize repeated tokens by count  | Reduce loops/repeated phrases                             | Too high: harms correctness for terms/IDs          |
| `presence_penalty`              | Penalize tokens seen at least once | Encourage novelty                                         | Too high: topic drift                              |
| `stop_sequences`                | Stop on delimiters                 | Clean boundaries (e.g., `<END>`, `###`, ``)               | Delimiter appears in normal text                   |

## Run the API (FastAPI)

### Start locally

```bash
cd api
uvicorn app:app --host 0.0.0.0 --port 8000
```

### Open docs

- http://localhost:8000/docs

### Example request

```bash
curl -X POST "http://localhost:8000/generate"   -H "Content-Type: application/json"   -d '{
    "prompt": "Return JSON and end with <END>.",
    "temperature": 0.2,
    "top_p": 0.9,
    "max_new_tokens": 200,
    "frequency_penalty": 0.2,
    "presence_penalty": 0.0,
    "stop_sequences": ["<END>"]
  }'
```

## Docker

### Build

```bash
docker build -t generation-controls -f api/Dockerfile .
```

### Run

```bash
docker run -p 8000:8000 generation-controls
```

## Kubernetes

```bash
kubectl apply -f api/k8s.yaml
kubectl get pods
kubectl get svc
```

## Observability (minimum)

Log/measure at least:

- `latency_ms` (p50/p95/p99)
- `generated_tokens`
- `stop_reason` (eos vs stop_sequence vs max_length)
- `temperature`, `top_p`, penalties (to debug regressions)
- Error rate by category (validation vs provider vs timeout)

Alerts to add early:

- p95 latency regression
- Sudden increase in tokens/request
- Spike in `max_length` stops (often indicates missing/incorrect stop delimiters)

## Production guidance

- Reject invalid configs at the boundary (do not silently clip)
- Always enforce max length and stop sequences
- Avoid logging raw prompts by default; log metadata and use redaction when needed
