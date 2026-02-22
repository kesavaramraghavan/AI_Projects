# Intelligent AI Web Chatbot
FastAPI • Session Memory • Dynamic UI • Monitoring Ready

## Overview
This project is a browser-based AI chatbot built with a production-minded backend. It’s not just a UI demo — it includes secure API handling, session state (memory), logging, and monitoring hooks.

### Built with
- FastAPI (backend API layer)
- LLM integration (AI response engine)
- Session-based conversational memory
- Static UI (HTML) with rotating background images
- API key authentication middleware
- Structured logging (tokens, time, cost estimation)
- Prometheus + Grafana monitoring readiness

## What this project does
- Provides an intelligent chat interface in the browser
- Remembers the conversation until the user clicks **Clear**
- Rotates background images every 5 seconds
- Protects API routes using an API key middleware
- Logs useful request metrics (tokens, estimated cost, duration)
- Exposes a metrics endpoint for monitoring in production setups

## When to use this architecture
This pattern is common in:
- AI-powered customer support bots
- Enterprise internal assistants
- SaaS chatbot platforms
- Knowledge-base conversational systems
- Recommendation or guided-shopping bots

Use this approach when you need:
- Backend-controlled LLM logic (no keys in frontend)
- Secure request handling
- Session memory
- A path to scaling/containerization
- Observability (metrics + logs)

## Project structure
```text
project-root/
├── api/
│   ├── app/
│   │   ├── main.py
│   │   └── config.py
│   └── static/
│       ├── index.html
│       └── backgrounds/
│           ├── bg1.jpg
│           ├── bg2.jpg
│           └── bg3.jpg
├── requirements.txt
└── README.md
```

## Features
- Stateful chat memory (until cleared)
- Dynamic rotating background images
- API key middleware security
- Static file serving via FastAPI
- Request logging with token + cost estimation
- Monitoring-ready `/metrics` endpoint (optional setup)

---

## Getting started (run locally)

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

### 3) Set your API key (environment variable)
Windows (CMD):
```bash
set API_KEY=your-secret-key
```

Mac / Linux:
```bash
export API_KEY=your-secret-key
```

### 4) Start the FastAPI server
From the project root:
```bash
uvicorn api.app.main:app --reload
```

If successful, you’ll see something like:
- `Uvicorn running on http://127.0.0.1:8000`

### 5) Open the chatbot UI
In your browser:
- http://127.0.0.1:8000/static/index.html

---

## Quick tests (verify everything works)

### Test 1 — Background rotation
- Watch the page: background should change every 5 seconds.

If images don’t load:
- Confirm images exist in `api/static/backgrounds/`.
- Try opening one directly, e.g. http://127.0.0.1:8000/static/backgrounds/bg1.jpg

### Test 2 — Conversation memory
1. Ask: `My name is John`
2. Then ask: `What is my name?`

The bot should remember.

Click **Clear** → memory should reset.

### Test 3 — API security (API key)
Send a request to a protected endpoint without the required API key header.

Expected result:
- `401 Unauthorized`

---

## Logging

### Where logs appear
By default, logs print to the terminal running Uvicorn.

Example log format:
```json
{
  "user_id": "anonymous",
  "prompt": "Hi",
  "prompt_tokens": 1,
  "completion_tokens": 10,
  "estimated_max_cost_usd": 0.000021,
  "duration_ms": 4006.6
}
```

### What gets logged
- Prompt tokens
- Completion tokens
- Estimated cost (max estimate)
- Response duration
- User ID
- Model response (if enabled in your logger)

### Persist logs to a file (optional)
In `main.py`, adjust logging config:
```python
import logging

logging.basicConfig(
    filename="app.log",
    level=logging.INFO
)
```

Logs will be written to:
- `project-root/app.log`

---

## Monitoring with Prometheus and Grafana (optional)

### Step 1 — Install Prometheus instrumentation
```bash
pip install prometheus-fastapi-instrumentator
```

Add to `main.py`:
```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

Metrics endpoint:
- http://127.0.0.1:8000/metrics

### Step 2 — Run Prometheus (Docker)
Create `prometheus.yml` in the project root:
```yaml
global:
  scrape_interval: 5s

scrape_configs:
  - job_name: 'chatbot'
    static_configs:
      - targets: ['host.docker.internal:8000']
```

Run Prometheus:

Windows PowerShell:
```bash
docker run -p 9090:9090 -v ${PWD}/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus
```

Prometheus UI:
- http://localhost:9090

### Step 3 — Run Grafana (Docker)
```bash
docker run -p 3000:3000 grafana/grafana
```

Grafana UI:
- http://localhost:3000

Default login:
- `admin / admin`

Add Prometheus as a data source:
- URL: http://host.docker.internal:9090

### What you can monitor
- Request rate and throughput
- Error rate (including auth failures)
- Latency and response time
- LLM response duration
- Container CPU/memory (when deployed with Docker/K8s)

---

## Security notes

### Already implemented
- API key middleware
- Static route exclusions (so UI assets load without auth)

### Recommended next steps
- JWT / OAuth authentication
- Rate limiting
- HTTPS
- CORS restriction
- Redis-backed session store
- Request validation via schemas (Pydantic models)

---

## Known limitations
- In-memory session storage (resets on restart)
- Not distributed (single instance only)
- No persistent DB
- No rate limiting yet

---

## Production evolution path
If you want to push this toward enterprise-grade:
- Add Redis for session/memory persistence
- Dockerize + add `docker-compose`
- Deploy to Kubernetes
- Add Horizontal Pod Autoscaler
- Add OpenTelemetry tracing
- Centralize logs (ELK / Loki)
- Implement cost-aware LLM routing
- Add streaming responses for better UX

---

## Why this repo is useful
This project demonstrates:
- Full-stack AI system design
- Secure backend API architecture
- Stateful conversation memory
- A dynamic frontend tied to backend behavior
- Monitoring readiness for production

It’s a solid foundation for:
- SaaS chatbot platforms
- Enterprise AI assistants
- Intelligent support systems
- AI product prototypes
