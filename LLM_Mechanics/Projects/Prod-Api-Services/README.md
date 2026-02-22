# Production AI API Service

FastAPI • Secure • Observable • Tested • Container-Ready

## Overview

This repository provides a production-oriented AI API service built with FastAPI.
It acts as a controlled gateway between clients and an LLM provider, adding security, observability, and cost awareness.

Use this service when you want a backend that can run locally, ship in a container, and plug into Prometheus/Grafana from day one.

## What this service solves

Many AI integrations break down in production because they ship without the basics:

- Security controls (who can call the API)
- Observability (what’s happening, where, and why)
- Cost awareness (tokens/cost per request)
- Clear separation of concerns (API vs. business/LLM logic)
- Tests (confidence to refactor and ship)

This API layer enforces:

- API key validation
- Request/response validation via Pydantic models
- Structured logging and metrics
- Optional caching to reduce repeated LLM calls

## Repository structure

Based on the current repo layout:

```text
project-root/
├── app/
│   ├── __pycache__/
│   ├── cache.py
│   ├── config.py
│   ├── logging_config.py
│   ├── main.py
│   ├── metrics.py
│   ├── middleware.py
│   ├── models.py
│   └── services.py
├── tests/
│   └── test_app.py
├── Dockerfile
├── requirements.txt
└── README.md
```

## File responsibilities

- `app/main.py`: Application entry point, FastAPI app initialization, middleware registration, routes, metrics exposure.
- `app/services.py`: LLM/provider integration, token counting, cost estimation, response formatting.
- `app/middleware.py`: API key authentication, request lifecycle hooks (timing/logging).
- `app/metrics.py`: Custom metrics; exposes `/metrics`.
- `app/models.py`: Pydantic request/response schemas for validation and typing.
- `app/config.py`: Centralized configuration loaded from environment variables.
- `app/logging_config.py`: Structured JSON logging configuration (stdout or file).
- `app/cache.py`: Optional caching layer (in-memory today; easy to swap for Redis).
- `tests/test_app.py`: Endpoint + behavior tests (auth, inference, error cases).

## Architecture (high level)

```text
Client
  ↓
FastAPI Application
  ↓
Middleware (Auth + Logging)
  ↓
Request Models (Validation)
  ↓
Service Layer (LLM + Token/Cost Logic)
  ↓
Cache (Optional)
  ↓
Response
  ↓
Metrics + Logs
```

## Core features

- API key authentication
- Structured JSON logging
- Token + cost estimation tracking
- Request duration measurement
- Prometheus `/metrics` endpoint
- Modular service architecture (clean separation of responsibilities)
- Test coverage support
- Cache abstraction layer

---

## Run locally

### 1) Create a virtual environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

Mac / Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Configure environment variables

Minimum:

- `API_KEY`: required for auth
- `MODEL_NAME`: model identifier used by your LLM provider integration

Windows (CMD):

```bash
set API_KEY=your-secret-key
set MODEL_NAME=your-model
```

Mac / Linux:

```bash
export API_KEY=your-secret-key
export MODEL_NAME=your-model
```

Tip: for local development, consider a `.env` file + `python-dotenv` (optional) if your `config.py` supports it.

### 4) Start the server

From the project root:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Health check:

- http://127.0.0.1:8000/health

---

## API endpoints

### Health

`GET /health`

Common uses:

- Kubernetes readiness/liveness probes
- Load balancer health checks

### Inference

`POST /inference`

Example request:

```json
{
  "prompt": "Explain transformers simply",
  "user_id": "123"
}
```

Example response:

```json
{
  "response": "...",
  "prompt_tokens": 20,
  "completion_tokens": 100,
  "estimated_cost_usd": 0.0021,
  "duration_ms": 845
}
```

---

## Security model

Authentication is enforced via an API key header:

- Header name: `x-api-key`
- Value: the same value as `API_KEY` in your environment

Requests without a valid key should return:

- `401 Unauthorized`

Implementation lives in `app/middleware.py`.

---

## Logging

Logs are structured JSON to make them easy to ship to centralized logging systems (ELK, Datadog, Loki, etc.).

Example:

```json
{
  "user_id": "123",
  "prompt_tokens": 18,
  "completion_tokens": 92,
  "estimated_cost_usd": 0.0019,
  "duration_ms": 732,
  "status": 200
}
```

Where logs go depends on `app/logging_config.py` (stdout by default is recommended for containers).

---

## Metrics & monitoring

Metrics endpoint:

- `GET /metrics`

Typical signals you can track:

- Request count / rate
- Error rate
- Latency (histograms)
- Status code distribution
- Auth failures

### Prometheus (Docker)

Create `prometheus.yml` in the project root:

```yaml
global:
  scrape_interval: 5s

scrape_configs:
  - job_name: "prod-ai-api"
    static_configs:
      - targets: ["host.docker.internal:8000"]
```

Run Prometheus:

Windows PowerShell:

```bash
docker run -p 9090:9090 -v ${PWD}/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus
```

Prometheus UI:

- http://localhost:9090

### Grafana (Docker)

Run Grafana:

```bash
docker run -p 3000:3000 grafana/grafana
```

Grafana UI:

- http://localhost:3000

Default login:

- `admin / admin`

Prometheus datasource URL:

- http://host.docker.internal:9090

---

## Testing

Run the test suite:

```bash
pytest
```

Suggested coverage goals:

- Auth middleware behavior (missing/invalid key)
- `/health` endpoint
- `/inference` happy path
- Provider failure handling + error responses
- Cache behavior (hit/miss)

---

## Containerization

A `Dockerfile` is included, so you can build and run the service in a container.

Typical flow:

```bash
docker build -t prod-ai-api .
docker run -p 8000:8000 -e API_KEY=your-secret-key -e MODEL_NAME=your-model prod-ai-api
```

---

## Production hardening roadmap

If you plan to run this at scale, consider adding:

- Redis (replace in-memory cache)
- Rate limiting and quotas (per API key / user / tenant)
- JWT/OAuth (stronger identity than static API keys)
- Timeouts + retries + circuit breaker around LLM provider calls
- OpenTelemetry tracing
- CI/CD pipeline (lint, tests, security scan, build, deploy)
- Streaming responses (better UX for long generations)

## Known limitations

- Cache is in-memory (not distributed)
- No tenant isolation (unless implemented via API keys/claims)
- No streaming inference by default
- Availability depends on the external LLM provider

## When you should use this

Use this service when:

- You need a centralized AI inference gateway
- You want production observability (logs + metrics)
- You need security enforcement at the API boundary
- You want to track cost/tokens per request

Avoid this if you only need:

- A single-user script
- A quick prototype with no monitoring
- A browser-based chatbot UI server
