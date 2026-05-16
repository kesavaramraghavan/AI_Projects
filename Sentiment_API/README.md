# Sentiment API

A lightweight, production-ready REST API that reads text and tells you whether it's **positive**, **negative**, or **neutral** - trained on your own data, served in milliseconds.

---

## What Does It Actually Do?

You send it a sentence. It tells you how that sentence _feels_.

```
"I love this product!" → positive (confidence: 0.94)
"Terrible experience." → negative (confidence: 0.91)
"The package arrived." → neutral  (confidence: 0.78)
```

That's it. No cloud dependencies, no API limits, no cost per call. You own the model can run locally.

---

## How It Works

1. **You train it** - send a list of labeled sentences (text + positive/negative/neutral label)
2. **It learns** - builds a text classifier using TF-IDF features + a calibrated SVM under the hood
3. **You call it** - send any text, get back a label + confidence score + per-class probabilities
4. **It remembers** - the trained model is saved to disk and auto-loaded on restart

The model uses **bigram TF-IDF** (captures two-word phrases like "not good") fed into a **Linear SVM with probability calibration** - fast, accurate, and interpretable.

---

## Quick Start

### 1. Install dependencies

```bash
pip install fastapi uvicorn scikit-learn pandas numpy
```

### 2. Run the server

```bash
python main.py
```

Server starts at `http://localhost:8001`. That's it.

### 3. Train your first model

You need at least **10 labeled sample examples** to train. Labels must be `positive`, `negative`, or `neutral`.

```bash
curl -X POST "http://localhost:8001/model/train" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-secret-key" \
  -d '{
    "samples": [
      {"text": "Amazing product, highly recommend!", "label": "positive"},
      {"text": "Worst purchase I have ever made.",   "label": "negative"},
      {"text": "Item arrived on Tuesday.",           "label": "neutral"},
      {"text": "Absolutely love it!",                "label": "positive"},
      {"text": "Complete waste of money.",           "label": "negative"},
      {"text": "Delivery took three days.",          "label": "neutral"},
      {"text": "Five stars, exceeded expectations.", "label": "positive"},
      {"text": "Broken on arrival, very unhappy.",   "label": "negative"},
      {"text": "Standard packaging, nothing special.", "label": "neutral"},
      {"text": "Would buy again without hesitation.", "label": "positive"}
    ]
  }'
```

**Response:**

```json
{
  "status": "trained",
  "samples": 10,
  "metrics": { "note": "no test split" }
}
```

> With 20+ samples, you'll also get accuracy, F1 score, and a confusion matrix automatically.

---

## API Reference

### `GET /health`

Check if the service is alive and the model is loaded.

```bash
curl http://localhost:8001/health
```

```json
{
  "service": "sentiment",
  "version": "2.1.0",
  "status": "healthy",
  "timestamp": "2026-05-16T19:00:00+00:00",
  "metrics": { "counters": {}, "histograms": {} }
}
```

---

### `POST /predict`

Analyze a single piece of text.

```bash
curl -X POST "http://localhost:8001/predict" \
  -H "Content-Type: application/json" \
  -d '{"text": "I love this product, it is amazing!"}'
```

```json
{
  "label": "positive",
  "confidence": 0.93,
  "scores": {
    "positive": 0.93,
    "negative": 0.04,
    "neutral": 0.03
  },
  "latency_ms": 1.8,
  "model_version": "2.1.0"
}
```

---

### `POST /predict/batch`

Analyze multiple texts in one shot - much faster than looping individual calls.

```bash
curl -X POST "http://localhost:8001/predict/batch" \
  -H "Content-Type: application/json" \
  -d '{"texts": ["Great service!", "Terrible experience", "Order confirmed."]}'
```

```json
{
  "results": [
    {"label": "positive", "confidence": 0.91, "scores": {...}},
    {"label": "negative", "confidence": 0.88, "scores": {...}},
    {"label": "neutral",  "confidence": 0.76, "scores": {...}}
  ],
  "count": 3,
  "latency_ms": 4.2,
  "model_version": "2.1.0"
}
```

---

### `POST /model/train` Requires API Key

Retrain the model with new labeled data. Replaces the existing model and saves it to disk.

> **Protected endpoint** - pass `X-API-Key` header.

| Field     | Type   | Required | Notes                                        |
| --------- | ------ | -------- | -------------------------------------------- |
| `samples` | array  | ✅       | List of `{text, label}` objects              |
| `label`   | string | ✅       | Must be `positive`, `negative`, or `neutral` |

**Minimum:** 10 samples. **Recommended:** 100+ for a proper train/test split and metrics.

---

## Authentication

The `/model/train` endpoint is protected by an API key. Set yours via environment variable:

```bash
export API_KEY="your-secret-key-here"
python main.py
```

Default (dev only): `dev-secret-key` - **change this before going to production.**

Pass it in the request header:

```
X-API-Key: your-secret-key-here
```

---

## Configuration

| Environment Variable | Default                        | What It Does                                   |
| -------------------- | ------------------------------ | ---------------------------------------------- |
| `API_KEY`            | `dev-secret-key`               | Protects the `/model/train` endpoint           |
| `MODELS_DIR`         | `.models/` (next to `main.py`) | Where the trained model is saved               |
| `LOG_LEVEL`          | `INFO`                         | Logging verbosity (`DEBUG`, `INFO`, `WARNING`) |

---

## Project Structure

```
.
├── main.py          # FastAPI app, model class, all API routes
├── utils.py         # Text cleaning, logging, metrics, model save/load helpers
└── .models/
    └── sentiment_model.pkl   # Auto-created after first training
```

---

## Understanding the Response Fields

| Field           | Meaning                                                       |
| --------------- | ------------------------------------------------------------- |
| `label`         | The predicted sentiment: `positive`, `negative`, or `neutral` |
| `confidence`    | How sure the model is (0.0–1.0). Higher = more certain        |
| `scores`        | Raw probability for _each_ class — always sums to 1.0         |
| `latency_ms`    | How long the prediction took in milliseconds                  |
| `model_version` | Version of the running model (`2.1.0`)                        |

---

## How Text Gets Cleaned

Before any prediction, your text is automatically:

- Normalized (Unicode NFKC)
- URLs replaced with the token `URL`
- Emails replaced with the token `EMAIL`
- Lowercased
- Extra whitespace collapsed

This means `"Check https://example.com for deals!!!"` and `"check URL for deals!!!"` are treated the same - which makes the model more robust.

---

## Model Quality (When You Have 20+ Samples)

With 20 or more training samples, the API automatically splits off 20% as a test set and returns:

```json
{
  "accuracy": 0.87,
  "f1_macro": 0.86,
  "f1_weighted": 0.87,
  "precision_macro": 0.88,
  "recall_macro": 0.85,
  "roc_auc": 0.94,
  "confusion_matrix": [
    [8, 1, 0],
    [0, 7, 1],
    [0, 0, 9]
  ],
  "classification_report": "..."
}
```

A good starting target for production use: **accuracy > 0.80, F1 macro > 0.75**.

---

## Production Checklist

- [ ] Set a strong `API_KEY` environment variable
- [ ] Train with at least **200+ diverse examples** per class
- [ ] Mount `.models/` as a persistent volume (Docker) so the model survives restarts
- [ ] Replace `SimpleMetrics` in `utils.py` with Prometheus for real observability
- [ ] Put a reverse proxy (nginx / Traefik) in front for TLS and rate limiting
- [ ] Set `CORS allow_origins` to your actual frontend domain instead of `"*"`

---

## Built With

| Library                                  | Purpose                                   |
| ---------------------------------------- | ----------------------------------------- |
| [FastAPI](https://fastapi.tiangolo.com)  | Web framework + automatic docs at `/docs` |
| [scikit-learn](https://scikit-learn.org) | TF-IDF vectorizer + Linear SVM classifier |
| [Uvicorn](https://www.uvicorn.org)       | ASGI server (runs the app)                |
| [Pandas](https://pandas.pydata.org)      | Training data handling                    |
| [Pydantic](https://docs.pydantic.dev)    | Request/response validation               |

---

## Interactive Docs

Once the server is running, visit:

```
http://localhost:8001/docs
```

You'll get a full interactive Swagger UI - try every endpoint right from the browser, no curl needed.

---

> Built by Kesava Ram Raghavan · Sentiment API v2.1.0
