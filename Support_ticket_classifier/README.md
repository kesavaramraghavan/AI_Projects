# 🎫 Support Ticket Classifier API

A self-training REST API that reads a customer support message and instantly tells you **what it's about** and **how urgent it is** - then routes it to the right team queue automatically.

---

## What Does It Actually Do?

You send it a support ticket. It gives you back three things:

```
"My order was marked delivered but I never received it."

→ category:  shipping        (confidence: 0.94)
→ priority:  P1-critical     (confidence: 0.89)
→ queue:     ESCALATION-FULFILLMENT-SUPPORT
```

No manual tagging. No routing rules. No human needed for the first pass.

---

## How It Works (Plain English)

1. **Starts itself** - on first launch, it trains on 200+ built-in labeled examples automatically. No setup needed.
2. **Two models, one call** - one XGBoost model predicts the _category_, another predicts the _priority_. Both run in a single `/classify` request.
3. **Suggests a queue** - based on the category + priority combo, it tells you exactly which support queue the ticket belongs in, including auto-escalation for critical issues.
4. **Saves its state** - the trained models are stored to disk and reloaded automatically on restart. Zero re-training overhead.

Under the hood: **TF-IDF bigrams** (captures phrases like "not delivered", "wrong item") fed into **XGBoost classifiers** - accurate, fast, and runs entirely on CPU.

---

## Categories & Priorities

### Categories

| Category    | What It Covers                                                      |
| ----------- | ------------------------------------------------------------------- |
| `billing`   | Duplicate charges, refund requests, invoice issues, payment methods |
| `technical` | App crashes, API errors, login failures, broken webhooks            |
| `account`   | Password resets, account deletion, 2FA, unauthorized access         |
| `shipping`  | Late delivery, wrong address, missing packages, tracking issues     |
| `returns`   | Damaged items, wrong item received, exchanges, refund timelines     |
| `general`   | Sales inquiries, API docs, partnership proposals, hiring            |

### Priority Levels

| Priority      | Meaning               | Typical Response Time |
| ------------- | --------------------- | --------------------- |
| `P1-critical` | Drop everything       | Immediate             |
| `P2-high`     | Same-day              | Within a few hours    |
| `P3-medium`   | Next business day     | 24 hours              |
| `P4-low`      | When bandwidth allows | 48–72 hours           |

### Queue Routing Logic

Critical tickets are automatically escalated with an `ESCALATION-` prefix:

```
billing   + P1-critical  →  ESCALATION-BILLING-SUPPORT
technical + P1-critical  →  ESCALATION-ENGINEERING-SUPPORT
shipping  + P1-critical  →  ESCALATION-FULFILLMENT-SUPPORT
account   + P1-critical  →  ESCALATION-ACCOUNT-SUPPORT
returns   + P1-critical  →  ESCALATION-RETURNS-SUPPORT

billing   + P2/P3/P4     →  billing-support
technical + P2/P3/P4     →  engineering-support
shipping  + P2/P3/P4     →  fulfillment-support
returns   + P2/P3/P4     →  returns-support
account   + P2/P3/P4     →  account-support
general   + any          →  general-support
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install fastapi uvicorn scikit-learn xgboost pandas numpy
```

### 2. Run the server

```bash
python main.py
```

Server starts at `http://localhost:8002`.
On first launch, it **trains and saves the model automatically** - takes about 5–10 seconds. Subsequent restarts load from disk instantly.

---

## API Reference

### `GET /health`

Check if the service is running and the model is loaded.

```bash
curl http://localhost:8002/health
```

**Response:**

```json
{
  "service": "support-ticket-classifier",
  "version": "1.0.0",
  "status": "healthy",
  "timestamp": "2026-05-16T20:00:00+00:00",
  "metrics": {
    "counters": { "classifier.classify.requests": 42 },
    "histograms": {}
  }
}
```

---

### `GET /model/info`

Inspect the loaded model - all classes, version, training timestamp, and evaluation scores.

```bash
curl http://localhost:8002/model/info
```

**Response:**

```json
{
  "version": "1.0.0",
  "trained_at": "2026-05-16T19:55:12.000000",
  "categories": [
    "account",
    "billing",
    "general",
    "returns",
    "shipping",
    "technical"
  ],
  "priorities": ["P1-critical", "P2-high", "P3-medium", "P4-low"],
  "metrics": {
    "category": {
      "accuracy": 0.94,
      "f1_macro": 0.93,
      "f1_weighted": 0.935,
      "precision_macro": 0.94,
      "recall_macro": 0.925
    },
    "priority": {
      "accuracy": 0.89,
      "f1_macro": 0.88,
      "f1_weighted": 0.885,
      "precision_macro": 0.89,
      "recall_macro": 0.875
    }
  }
}
```

---

### `POST /classify`

Classify a single support ticket. Returns category, priority, confidence scores, and suggested queue.

**Request fields:**

| Field       | Type   | Required | Notes                                             |
| ----------- | ------ | -------- | ------------------------------------------------- |
| `text`      | string | ✅       | Ticket content - 1 to 20,000 characters           |
| `ticket_id` | string | ❌       | Your internal ticket ID, passed through unchanged |

---

#### Example 1 - Critical Technical Issue (Auto-Escalated)

```bash
curl -X POST "http://localhost:8002/classify" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The app crashes every time I click the export button. This is blocking our entire team right now.",
    "ticket_id": "TKT-001"
  }'
```

**Response:**

```json
{
  "ticket_id": "TKT-001",
  "category": "technical",
  "category_confidence": 0.9721,
  "category_scores": {
    "technical": 0.9721,
    "billing": 0.0083,
    "account": 0.0071,
    "general": 0.0062,
    "returns": 0.0041,
    "shipping": 0.0022
  },
  "priority": "P1-critical",
  "priority_confidence": 0.9103,
  "priority_scores": {
    "P1-critical": 0.9103,
    "P2-high": 0.0621,
    "P3-medium": 0.0201,
    "P4-low": 0.0075
  },
  "suggested_queue": "ESCALATION-ENGINEERING-SUPPORT",
  "latency_ms": 3.41
}
```

---

#### Example 2 - Billing Question (Low Priority)

```bash
curl -X POST "http://localhost:8002/classify" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What payment methods do you accept?",
    "ticket_id": "TKT-002"
  }'
```

**Response:**

```json
{
  "ticket_id": "TKT-002",
  "category": "billing",
  "category_confidence": 0.9344,
  "category_scores": {
    "billing": 0.9344,
    "general": 0.0412,
    "technical": 0.0244
  },
  "priority": "P4-low",
  "priority_confidence": 0.8876,
  "priority_scores": {
    "P4-low": 0.8876,
    "P3-medium": 0.0901,
    "P2-high": 0.0223
  },
  "suggested_queue": "billing-support",
  "latency_ms": 2.18
}
```

---

#### Example 3 - Unauthorized Account Access (Auto-Escalated)

```bash
curl -X POST "http://localhost:8002/classify" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Someone logged into my account from a different country. I did not authorize this at all.",
    "ticket_id": "TKT-003"
  }'
```

**Response:**

```json
{
  "ticket_id": "TKT-003",
  "category": "account",
  "category_confidence": 0.9512,
  "category_scores": {
    "account": 0.9512,
    "technical": 0.0291,
    "general": 0.0197
  },
  "priority": "P1-critical",
  "priority_confidence": 0.9288,
  "priority_scores": {
    "P1-critical": 0.9288,
    "P2-high": 0.0512,
    "P3-medium": 0.0143,
    "P4-low": 0.0057
  },
  "suggested_queue": "ESCALATION-ACCOUNT-SUPPORT",
  "latency_ms": 2.97
}
```

---

#### Example 4 - Missing Package (Auto-Escalated)

```bash
curl -X POST "http://localhost:8002/classify" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "My package was marked as delivered three days ago but I never received it. Please investigate urgently.",
    "ticket_id": "TKT-004"
  }'
```

**Response:**

```json
{
  "ticket_id": "TKT-004",
  "category": "shipping",
  "category_confidence": 0.9631,
  "priority": "P1-critical",
  "priority_confidence": 0.9011,
  "suggested_queue": "ESCALATION-FULFILLMENT-SUPPORT",
  "latency_ms": 2.54
}
```

---

#### Example 5 - Return Request (Medium Priority)

```bash
curl -X POST "http://localhost:8002/classify" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I would like to exchange my item for a different size. How do I start the return process?",
    "ticket_id": "TKT-005"
  }'
```

**Response:**

```json
{
  "ticket_id": "TKT-005",
  "category": "returns",
  "category_confidence": 0.9108,
  "priority": "P3-medium",
  "priority_confidence": 0.8632,
  "suggested_queue": "returns-support",
  "latency_ms": 1.98
}
```

---

#### Example 6 - General Inquiry (Low Priority)

```bash
curl -X POST "http://localhost:8002/classify" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Can you provide documentation for your REST API? I am evaluating your platform for our team.",
    "ticket_id": "TKT-006"
  }'
```

**Response:**

```json
{
  "ticket_id": "TKT-006",
  "category": "general",
  "category_confidence": 0.8977,
  "priority": "P4-low",
  "priority_confidence": 0.9102,
  "suggested_queue": "general-support",
  "latency_ms": 1.72
}
```

---

### `POST /classify/batch`

Classify up to **256 tickets** in one request - much faster than looping individual calls.

```bash
curl -X POST "http://localhost:8002/classify/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "tickets": [
      {"text": "I was charged twice this month for the same plan.",                          "ticket_id": "TKT-010"},
      {"text": "API integration keeps returning 500 errors since your last deploy.",         "ticket_id": "TKT-011"},
      {"text": "How do I add a new team member to my workspace?",                            "ticket_id": "TKT-012"},
      {"text": "My package was marked as delivered but I never received it.",                "ticket_id": "TKT-013"},
      {"text": "I received the wrong item. I ordered size M but got size XL.",               "ticket_id": "TKT-014"},
      {"text": "My refund still has not appeared after 10 business days.",                   "ticket_id": "TKT-015"},
      {"text": "Password reset email is not arriving. I have tried multiple times.",         "ticket_id": "TKT-016"}
    ]
  }'
```

**Response:**

```json
{
  "results": [
    {
      "ticket_id": "TKT-010",
      "category": "billing",
      "priority": "P2-high",
      "suggested_queue": "billing-support"
    },
    {
      "ticket_id": "TKT-011",
      "category": "technical",
      "priority": "P1-critical",
      "suggested_queue": "ESCALATION-ENGINEERING-SUPPORT"
    },
    {
      "ticket_id": "TKT-012",
      "category": "account",
      "priority": "P4-low",
      "suggested_queue": "account-support"
    },
    {
      "ticket_id": "TKT-013",
      "category": "shipping",
      "priority": "P1-critical",
      "suggested_queue": "ESCALATION-FULFILLMENT-SUPPORT"
    },
    {
      "ticket_id": "TKT-014",
      "category": "returns",
      "priority": "P2-high",
      "suggested_queue": "returns-support"
    },
    {
      "ticket_id": "TKT-015",
      "category": "returns",
      "priority": "P2-high",
      "suggested_queue": "returns-support"
    },
    {
      "ticket_id": "TKT-016",
      "category": "technical",
      "priority": "P2-high",
      "suggested_queue": "engineering-support"
    }
  ],
  "count": 7,
  "latency_ms": 14.22
}
```

---

## Understanding the Response Fields

| Field                 | Meaning                                                                                        |
| --------------------- | ---------------------------------------------------------------------------------------------- |
| `ticket_id`           | Your ID echoed back - useful for matching responses in bulk workflows                          |
| `category`            | What the ticket is about (`billing`, `technical`, `account`, `shipping`, `returns`, `general`) |
| `category_confidence` | How sure the model is about the category (0.0 – 1.0)                                           |
| `category_scores`     | Raw probability for every category - always sums to 1.0                                        |
| `priority`            | Urgency level: `P1-critical`, `P2-high`, `P3-medium`, or `P4-low`                              |
| `priority_confidence` | How sure the model is about the priority                                                       |
| `priority_scores`     | Raw probability for every priority level - always sums to 1.0                                  |
| `suggested_queue`     | Where to route this ticket - prefixed with `ESCALATION-` for all P1 tickets                    |
| `latency_ms`          | Time taken to produce the prediction, in milliseconds                                          |

---

## How Text Gets Cleaned

Before prediction, every ticket is automatically:

- Unicode-normalized (NFKC)
- URLs replaced with the token `URL`
- Email addresses replaced with `EMAIL`
- Lowercased
- Extra whitespace collapsed

This makes the model robust to messy real-world input like forwarded email threads, copy-pasted URLs, and inconsistent formatting.

---

## Training Data

The model ships with **52 seed examples** across 6 categories, automatically augmented to **208 samples** by prepending `RE:`, `FWD:`, and appending `"Please help ASAP."` to each example - simulating real forwarded email threads and urgent follow-ups.

To improve accuracy in production, extend or replace `RAW_DATA` in `main.py` with your real historical ticket data and restart - it retrains automatically.

A good target for production readiness:

| Metric            | Minimum Target |
| ----------------- | -------------- |
| Category accuracy | > 0.88         |
| Priority accuracy | > 0.82         |
| F1 macro (both)   | > 0.80         |

---

## Project Structure

```
.
├── main.py           # FastAPI app, TicketClassifier, all routes, seed data
├── utils.py          # Shared helpers: text cleaning, logging, metrics, artifact I/O
└── .models/
    └── category.pkl  # Auto-created on first run (stores both category + priority models)
```

> Both models (category and priority) are stored in a single artifact file for simplicity.

---

## Configuration

| Environment Variable | Default                      | What It Does                                  |
| -------------------- | ---------------------------- | --------------------------------------------- |
| `MODELS_DIR`         | `.models/` next to `main.py` | Where trained model artifacts are saved       |
| `LOG_LEVEL`          | `INFO`                       | Logging verbosity: `DEBUG`, `INFO`, `WARNING` |

---

## Production Checklist

- [ ] Replace `RAW_DATA` with 500+ real labeled tickets per category for better accuracy
- [ ] Add an API key to `/classify` and `/classify/batch` endpoints before public exposure
- [ ] Mount `.models/` as a persistent Docker volume so models survive container restarts
- [ ] Change `allow_origins=["*"]` in CORS middleware to your actual frontend domain
- [ ] Swap `SimpleMetrics` in `utils.py` for Prometheus + Grafana for real-time queue visibility
- [ ] Add a `/model/retrain` endpoint so support ops can retrain without a full redeploy
- [ ] Log predictions to a database to build a feedback loop for continuous improvement

---

## Built With

| Library                                   | Purpose                                                    |
| ----------------------------------------- | ---------------------------------------------------------- |
| [FastAPI](https://fastapi.tiangolo.com)   | Web framework + auto-generated Swagger docs at `/docs`     |
| [XGBoost](https://xgboost.readthedocs.io) | Gradient boosted classifier for both category and priority |
| [scikit-learn](https://scikit-learn.org)  | TF-IDF vectorizer, train/test split, evaluation metrics    |
| [Uvicorn](https://www.uvicorn.org)        | ASGI server that runs the FastAPI app                      |
| [Pydantic](https://docs.pydantic.dev)     | Request/response validation with field-level constraints   |

---

## Interactive Docs

Once the server is running, open your browser and visit:

```
http://localhost:8002/docs
```

You'll get the full Swagger UI - test every endpoint directly from the browser without needing curl.

---

> Built by Kesava Ram Raghavan · Support Ticket Classifier v1.0.0
