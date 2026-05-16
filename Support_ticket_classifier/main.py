from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import (
    artifact_exists, build_health_response, clean_text,
    evaluate_classifier, get_logger, load_artifact,
    metrics, save_artifact, timed,
)

logger = get_logger("ticket_classifier")

MODEL_NAME_CAT  = "category"
MODEL_NAME_PRIO = "priority"
MODEL_VERSION   = "1.0.0"

# ─── Synthetic Training Data ──────────────────────────────────────────────────

RAW_DATA: List[Dict[str, str]] = [
    # billing
    {"text": "I was charged twice for my subscription this month.", "category": "billing", "priority": "P2-high"},
    {"text": "My invoice shows an incorrect amount, please fix it.", "category": "billing", "priority": "P2-high"},
    {"text": "How do I update my payment method on file?", "category": "billing", "priority": "P3-medium"},
    {"text": "I need a refund for a duplicate charge.", "category": "billing", "priority": "P2-high"},
    {"text": "Can you send me a copy of my last invoice?", "category": "billing", "priority": "P4-low"},
    {"text": "My credit card was declined during checkout.", "category": "billing", "priority": "P2-high"},
    {"text": "Please cancel my subscription and refund the unused days.", "category": "billing", "priority": "P2-high"},
    {"text": "What payment methods do you accept?", "category": "billing", "priority": "P4-low"},
    {"text": "I was billed for a plan I downgraded from last week.", "category": "billing", "priority": "P2-high"},
    {"text": "How do I view my billing history?", "category": "billing", "priority": "P4-low"},
    # technical
    {"text": "The application crashes every time I click the export button.", "category": "technical", "priority": "P1-critical"},
    {"text": "I cannot log in; the page just refreshes endlessly.", "category": "technical", "priority": "P1-critical"},
    {"text": "API integration is returning 500 errors.", "category": "technical", "priority": "P1-critical"},
    {"text": "The dashboard does not load any data for my account.", "category": "technical", "priority": "P2-high"},
    {"text": "Password reset email is not arriving.", "category": "technical", "priority": "P2-high"},
    {"text": "My webhooks have stopped firing since the last update.", "category": "technical", "priority": "P1-critical"},
    {"text": "How do I configure SSO with Okta?", "category": "technical", "priority": "P3-medium"},
    {"text": "The mobile app is showing outdated data.", "category": "technical", "priority": "P3-medium"},
    {"text": "Export to CSV is producing corrupt files.", "category": "technical", "priority": "P2-high"},
    {"text": "Notifications are not being delivered to my email.", "category": "technical", "priority": "P2-high"},
    # account
    {"text": "I need to transfer my account to a different email address.", "category": "account", "priority": "P3-medium"},
    {"text": "How do I add a team member to my workspace?", "category": "account", "priority": "P4-low"},
    {"text": "Can I merge two accounts into one?", "category": "account", "priority": "P3-medium"},
    {"text": "I forgot my password and the reset link is expired.", "category": "account", "priority": "P2-high"},
    {"text": "Please delete my account and all associated data.", "category": "account", "priority": "P2-high"},
    {"text": "How do I change my account username?", "category": "account", "priority": "P4-low"},
    {"text": "My account has been locked due to too many login attempts.", "category": "account", "priority": "P2-high"},
    {"text": "How do I set up two-factor authentication?", "category": "account", "priority": "P4-low"},
    {"text": "I need to update the company name on my account.", "category": "account", "priority": "P4-low"},
    {"text": "Someone may have accessed my account without permission.", "category": "account", "priority": "P1-critical"},
    # shipping
    {"text": "My order was supposed to arrive 3 days ago and has not.", "category": "shipping", "priority": "P2-high"},
    {"text": "The tracking number provided is not working.", "category": "shipping", "priority": "P3-medium"},
    {"text": "Can I change my delivery address after placing the order?", "category": "shipping", "priority": "P2-high"},
    {"text": "My package was marked delivered but I never received it.", "category": "shipping", "priority": "P1-critical"},
    {"text": "Do you ship internationally?", "category": "shipping", "priority": "P4-low"},
    {"text": "How long does standard shipping take to California?", "category": "shipping", "priority": "P4-low"},
    {"text": "I need expedited shipping for my order.", "category": "shipping", "priority": "P2-high"},
    {"text": "The courier attempted delivery but I was not home.", "category": "shipping", "priority": "P3-medium"},
    # returns
    {"text": "I want to return the product I received last week.", "category": "returns", "priority": "P3-medium"},
    {"text": "The item I received is damaged. I need a replacement.", "category": "returns", "priority": "P2-high"},
    {"text": "How long does the refund process take?", "category": "returns", "priority": "P3-medium"},
    {"text": "I received the wrong item in my order.", "category": "returns", "priority": "P2-high"},
    {"text": "I would like to exchange my item for a different size.", "category": "returns", "priority": "P3-medium"},
    {"text": "What is your return policy for digital products?", "category": "returns", "priority": "P4-low"},
    {"text": "My refund still has not appeared after 10 business days.", "category": "returns", "priority": "P2-high"},
    # general
    {"text": "I have a question about your enterprise plan.", "category": "general", "priority": "P3-medium"},
    {"text": "Can you provide documentation for the REST API?", "category": "general", "priority": "P4-low"},
    {"text": "I am a journalist writing an article about your company.", "category": "general", "priority": "P4-low"},
    {"text": "How do I contact your sales team?", "category": "general", "priority": "P4-low"},
    {"text": "Are you hiring software engineers?", "category": "general", "priority": "P4-low"},
    {"text": "I have a partnership proposal I'd like to discuss.", "category": "general", "priority": "P3-medium"},
]


def build_dataset() -> pd.DataFrame:
    df = pd.DataFrame(RAW_DATA)
    aug = []
    for _, row in df.iterrows():
        aug.append({"text": "RE: " + row["text"], "category": row["category"], "priority": row["priority"]})
        aug.append({"text": "FWD: " + row["text"], "category": row["category"], "priority": row["priority"]})
        aug.append({"text": row["text"] + " Please help ASAP.", "category": row["category"], "priority": row["priority"]})
    return pd.concat([df, pd.DataFrame(aug)], ignore_index=True).sample(frac=1, random_state=42)


# ─── Model ────────────────────────────────────────────────────────────────────

class TicketClassifier:
    def __init__(self):
        self.cat_pipeline:  Optional[Pipeline] = None
        self.prio_pipeline: Optional[Pipeline] = None
        self.cat_encoder   = LabelEncoder()
        self.prio_encoder  = LabelEncoder()
        self._metrics: Dict[str, Any] = {}
        self._trained_at: Optional[str] = None

    def _make_pipeline(self, n_classes: int) -> Pipeline:
        tfidf = TfidfVectorizer(
            ngram_range=(1, 2), min_df=1, max_features=30_000,
            sublinear_tf=True, strip_accents="unicode",
        )
        xgb = XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            use_label_encoder=False,
            eval_metric="mlogloss",
            num_class=n_classes if n_classes > 2 else None,
            objective="multi:softprob" if n_classes > 2 else "binary:logistic",
            random_state=42,
            n_jobs=-1,
        )
        return Pipeline([("tfidf", tfidf), ("clf", xgb)])

    @timed("classifier.train")
    def train(self, df: pd.DataFrame) -> Dict[str, Any]:
        logger.info("Training ticket classifier on %d samples …", len(df))
        texts = df["text"].apply(clean_text).tolist()

        # ── Category ──
        y_cat  = self.cat_encoder.fit_transform(df["category"])
        Xtr, Xte, ytr, yte = train_test_split(texts, y_cat, test_size=0.2, stratify=y_cat, random_state=42)
        self.cat_pipeline = self._make_pipeline(len(self.cat_encoder.classes_))
        self.cat_pipeline.fit(Xtr, ytr)
        cat_pred  = self.cat_pipeline.predict(Xte)
        cat_proba = self.cat_pipeline.predict_proba(Xte)
        cat_eval  = evaluate_classifier(yte, cat_pred, cat_proba, list(self.cat_encoder.classes_))

        # ── Priority ──
        y_prio = self.prio_encoder.fit_transform(df["priority"])
        Xtr2, Xte2, ytr2, yte2 = train_test_split(texts, y_prio, test_size=0.2, stratify=y_prio, random_state=99)
        self.prio_pipeline = self._make_pipeline(len(self.prio_encoder.classes_))
        self.prio_pipeline.fit(Xtr2, ytr2)
        prio_pred  = self.prio_pipeline.predict(Xte2)
        prio_proba = self.prio_pipeline.predict_proba(Xte2)
        prio_eval  = evaluate_classifier(yte2, prio_pred, prio_proba, list(self.prio_encoder.classes_))

        self._metrics = {"category": cat_eval, "priority": prio_eval}
        self._trained_at = pd.Timestamp.utcnow().isoformat()
        logger.info("Category accuracy=%.4f  Priority accuracy=%.4f",
                    cat_eval["accuracy"], prio_eval["accuracy"])
        return self._metrics

    @timed("classifier.predict")
    def predict(self, text: str) -> Dict[str, Any]:
        cleaned = clean_text(text)
        cat_proba  = self.cat_pipeline.predict_proba([cleaned])[0]
        prio_proba = self.prio_pipeline.predict_proba([cleaned])[0]
        cat_idx    = int(np.argmax(cat_proba))
        prio_idx   = int(np.argmax(prio_proba))
        return {
            "category":          self.cat_encoder.inverse_transform([cat_idx])[0],
            "category_confidence": round(float(cat_proba[cat_idx]), 4),
            "category_scores":   {c: round(float(p), 4) for c, p in
                                   zip(self.cat_encoder.classes_, cat_proba)},
            "priority":          self.prio_encoder.inverse_transform([prio_idx])[0],
            "priority_confidence": round(float(prio_proba[prio_idx]), 4),
            "priority_scores":   {c: round(float(p), 4) for c, p in
                                   zip(self.prio_encoder.classes_, prio_proba)},
            "suggested_queue":   self._queue_name(
                self.cat_encoder.inverse_transform([cat_idx])[0],
                self.prio_encoder.inverse_transform([prio_idx])[0]
            ),
        }

    @staticmethod
    def _queue_name(category: str, priority: str) -> str:
        queue_map = {
            "billing":   "billing-support",
            "technical": "engineering-support",
            "account":   "account-support",
            "shipping":  "fulfillment-support",
            "returns":   "returns-support",
            "general":   "general-support",
        }
        queue = queue_map.get(category, "general-support")
        if priority == "P1-critical":
            queue = "ESCALATION-" + queue.upper()
        return queue

    def save(self):
        save_artifact({"cat_pipeline": self.cat_pipeline,
                       "prio_pipeline": self.prio_pipeline,
                       "cat_encoder": self.cat_encoder,
                       "prio_encoder": self.prio_encoder,
                       "metrics": self._metrics,
                       "trained_at": self._trained_at}, MODEL_NAME_CAT)

    @classmethod
    def load(cls) -> "TicketClassifier":
        obj = load_artifact(MODEL_NAME_CAT)
        m = cls()
        m.cat_pipeline  = obj["cat_pipeline"]
        m.prio_pipeline = obj["prio_pipeline"]
        m.cat_encoder   = obj["cat_encoder"]
        m.prio_encoder  = obj["prio_encoder"]
        m._metrics      = obj.get("metrics", {})
        m._trained_at   = obj.get("trained_at")
        return m


# ─── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(title="Support Ticket Classifier", version=MODEL_VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_model: Optional[TicketClassifier] = None


class ClassifyIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=20_000)
    ticket_id: Optional[str] = None


class BatchClassifyIn(BaseModel):
    tickets: List[ClassifyIn] = Field(..., max_length=256)


@app.on_event("startup")
async def startup():
    global _model
    if artifact_exists(MODEL_NAME_CAT):
        _model = TicketClassifier.load()
    else:
        _model = TicketClassifier()
        _model.train(build_dataset())
        _model.save()
    logger.info("Support Ticket Classifier ready.")


@app.get("/health")
def health():
    return build_health_response("support-ticket-classifier", MODEL_VERSION, _model is not None)


@app.post("/classify")
def classify(body: ClassifyIn):
    if _model is None:
        raise HTTPException(503, "Model not loaded")
    t0 = time.perf_counter()
    result = _model.predict(body.text)
    latency_ms = (time.perf_counter() - t0) * 1000
    metrics.inc("classifier.classify.requests")
    return {"ticket_id": body.ticket_id, **result, "latency_ms": round(latency_ms, 2)}


@app.post("/classify/batch")
def classify_batch(body: BatchClassifyIn):
    if _model is None:
        raise HTTPException(503, "Model not loaded")
    t0 = time.perf_counter()
    results = [{"ticket_id": t.ticket_id, **_model.predict(t.text)} for t in body.tickets]
    return {"results": results, "count": len(results),
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2)}


@app.get("/model/info")
def model_info():
    return {"version": MODEL_VERSION, "trained_at": _model._trained_at,
            "categories": list(_model.cat_encoder.classes_),
            "priorities": list(_model.prio_encoder.classes_),
            "metrics": _model._metrics}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)