from __future__ import annotations

import os
import time
import numpy as np
import pandas as pd
import uvicorn

from typing import List, Dict, Optional

from fastapi import FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader

from pydantic import BaseModel

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split


from utils import (
    clean_text,
    get_logger,
    timed,
    save_artifact,
    load_artifact,
    artifact_exists,
    build_health_response,
    evaluate_classifier,
    metrics
)

logger = get_logger("sentiment-api")

MODEL_NAME = "sentiment_model"
MODEL_VERSION = "2.1.0"
API_KEY = os.getenv("API_KEY", "dev-secret-key")

VALID_LABELS = {"positive", "negative", "neutral"}

class SentimentModel:
    def __init__(self):
        self.pipeline: Optional[Pipeline] = None
        self.encoder = LabelEncoder()
        self.metrics: Dict = {}
        self.trained_at: Optional[str] = None

    def _build_pipeline(self) -> Pipeline:
        base = LinearSVC(
            C=1.0,
            class_weight="balanced",
            max_iter=3000
        )

        clf = CalibratedClassifierCV(base, cv=3)

        return Pipeline([
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 2),
                max_features=20000,
                min_df=2,
                sublinear_tf=True
            )),
            ("clf", clf)
        ])

    @timed("train")
    def train(self, df: pd.DataFrame) -> Dict:

        if len(df) < 10:
            raise HTTPException(400, "Need at least 10 samples")

        if "text" not in df or "label" not in df:
            raise HTTPException(400, "Dataset must contain text + label")

        bad = set(df["label"]) - VALID_LABELS
        if bad:
            raise HTTPException(400, f"Invalid labels: {bad}")

        X = df["text"].astype(str).map(clean_text).tolist()
        y = self.encoder.fit_transform(df["label"])

        if len(df) >= 20:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y,
                test_size=0.2,
                stratify=y,
                random_state=42
            )
        else:
            X_train, y_train = X, y
            X_test, y_test = None, None

        self.pipeline = self._build_pipeline()
        self.pipeline.fit(X_train, y_train)

        # evaluation
        if X_test is not None:
            preds = self.pipeline.predict(X_test)
            probs = self.pipeline.predict_proba(X_test)

            self.metrics = evaluate_classifier(
                y_test,
                preds,
                probs,
                labels=list(self.encoder.classes_)
            )
        else:
            self.metrics = {"note": "no test split"}

        self.trained_at = pd.Timestamp.utcnow().isoformat()

        return self.metrics

    @timed("predict")
    def predict(self, text: str) -> Dict:

        if not self.pipeline:
            raise RuntimeError("Model not trained")

        text = clean_text(text)
        probs = self.pipeline.predict_proba([text])[0]

        idx = int(np.argmax(probs))
        label = self.encoder.inverse_transform([idx])[0]

        return {
            "label": label,
            "confidence": float(probs[idx]),
            "scores": {
                cls: float(p)
                for cls, p in zip(self.encoder.classes_, probs)
            }
        }

    @timed("batch_predict")
    def predict_batch(self, texts: List[str]) -> List[Dict]:

        if not self.pipeline:
            raise RuntimeError("Model not trained")

        cleaned = [clean_text(t) for t in texts]
        probs = self.pipeline.predict_proba(cleaned)

        results = []
        for p in probs:
            idx = int(np.argmax(p))
            results.append({
                "label": self.encoder.inverse_transform([idx])[0],
                "confidence": float(p[idx]),
                "scores": {
                    cls: float(score)
                    for cls, score in zip(self.encoder.classes_, p)
                }
            })

        return results

    def save(self):
        save_artifact({
            "pipeline": self.pipeline,
            "encoder": self.encoder,
            "metrics": self.metrics,
            "trained_at": self.trained_at,
            "version": MODEL_VERSION
        }, MODEL_NAME)

    @classmethod
    def load(cls) -> "SentimentModel":
        obj = load_artifact(MODEL_NAME)

        m = cls()
        m.pipeline = obj["pipeline"]

        m.encoder = (
            obj.get("encoder")
            or obj.get("label_encoder")
            or LabelEncoder()
        )

        m.metrics = obj.get("metrics", {})
        m.trained_at = obj.get("trained_at")

        return m

# ────── FASTAPI ───────────────────────────────────────

app = FastAPI(title="Sentiment API", version=MODEL_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

_model: Optional[SentimentModel] = None


def require_key(key: str = Security(api_key_header)):
    if key != API_KEY:
        raise HTTPException(403, "Invalid API key")
    return key


class PredictIn(BaseModel):
    text: str


class BatchIn(BaseModel):
    texts: List[str]


class TrainIn(BaseModel):
    samples: List[Dict[str, str]]


@app.on_event("startup")
def startup():
    global _model

    if artifact_exists(MODEL_NAME):
        logger.info("Loading model...")
        _model = SentimentModel.load()
    else:
        logger.info("No model found, creating new one")
        _model = SentimentModel()


@app.get("/health")
def health():
    return build_health_response("sentiment", MODEL_VERSION, _model is not None)


@app.post("/predict")
def predict(body: PredictIn):

    t0 = time.perf_counter()
    result = _model.predict(body.text)
    latency = (time.perf_counter() - t0) * 1000

    metrics.inc("predict.requests")
    metrics.observe("predict.latency_ms", latency)

    return {
        **result,
        "latency_ms": round(latency, 2),
        "model_version": MODEL_VERSION
    }


@app.post("/predict/batch")
def batch(body: BatchIn):

    t0 = time.perf_counter()
    results = _model.predict_batch(body.texts)
    latency = (time.perf_counter() - t0) * 1000

    metrics.inc("batch.requests")

    return {
        "results": results,
        "count": len(results),
        "latency_ms": round(latency, 2),
        "model_version": MODEL_VERSION
    }


@app.post("/model/train")
def train(body: TrainIn, _key: str = Security(require_key)):

    global _model

    df = pd.DataFrame(body.samples)

    if len(df) < 10:
        raise HTTPException(400, "Need at least 10 samples")

    bad = set(df["label"]) - VALID_LABELS
    if bad:
        raise HTTPException(400, f"Invalid labels: {bad}")

    _model = SentimentModel()
    metrics_out = _model.train(df)
    _model.save()

    return {
        "status": "trained",
        "samples": len(df),
        "metrics": metrics_out
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)