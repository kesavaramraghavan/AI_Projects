from __future__ import annotations

import logging
import os
import pickle
import re
import time
import unicodedata
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np

# ─── Logging ──────────────────────────────────────────────────────────────────

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_LEVEL  = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(format=LOG_FORMAT, level=LOG_LEVEL)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    return logger


# ─── Timing / Metrics ─────────────────────────────────────────────────────────


class SimpleMetrics:
    """In-process metrics collector (kindly swap for Prometheus in prod)."""

    def __init__(self):
        self._counters: Dict[str, int] = {}
        self._histograms: Dict[str, List[float]] = {}

    def inc(self, name: str, amount: int = 1) -> None:
        self._counters[name] = self._counters.get(name, 0) + amount

    def observe(self, name: str, value: float) -> None:
        self._histograms.setdefault(name, []).append(value)

    def summary(self) -> Dict[str, Any]:
        hist_summary = {}
        for k, vals in self._histograms.items():
            arr = np.array(vals)
            hist_summary[k] = {
                "count": len(arr),
                "mean": float(arr.mean()),
                "p50": float(np.percentile(arr, 50)),
                "p95": float(np.percentile(arr, 95)),
                "p99": float(np.percentile(arr, 99)),
            }
        return {"counters": dict(self._counters), "histograms": hist_summary}


metrics = SimpleMetrics()


def timed(metric_name: Optional[str] = None):
    """Decorator: records latency in milliseconds."""
    def decorator(fn: Callable):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = fn(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000
            name = metric_name or f"{fn.__module__}.{fn.__qualname__}"
            metrics.observe(f"{name}.latency_ms", elapsed_ms)
            return result
        return wrapper
    return decorator


# ─── Text Preprocessing ───────────────────────────────────────────────────────

_URL_RE   = re.compile(r"https?://\S+|www\.\S+")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}")
_NUM_RE   = re.compile(r"\b\d+\b")
_MULTI_SPACE = re.compile(r"\s+")


def clean_text(
    text: str,
    *,
    lower: bool = True,
    strip_urls: bool = True,
    strip_emails: bool = True,
    strip_numbers: bool = False,
    max_length: Optional[int] = None,
) -> str:
    if not isinstance(text, str):
        text = str(text)
    text = unicodedata.normalize("NFKC", text)
    if strip_urls:
        text = _URL_RE.sub(" URL ", text)
    if strip_emails:
        text = _EMAIL_RE.sub(" EMAIL ", text)
    if strip_numbers:
        text = _NUM_RE.sub(" NUM ", text)
    text = _MULTI_SPACE.sub(" ", text).strip()
    if lower:
        text = text.lower()
    if max_length:
        text = text[:max_length]
    return text


# ─── Model Artifact Helpers ────────────────────────────────────────────────────

MODELS_DIR = Path(os.getenv("MODELS_DIR", str(Path(__file__).parent / ".models")))
MODELS_DIR.mkdir(parents=True, exist_ok=True)


def save_artifact(obj: Any, name: str) -> Path:
    path = MODELS_DIR / f"{name}.pkl"
    with open(path, "wb") as f:
        pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
    get_logger("utils").info("Saved artifact → %s", path)
    return path


def load_artifact(name: str) -> Any:
    path = MODELS_DIR / f"{name}.pkl"
    if not path.exists():
        raise FileNotFoundError(f"Artifact not found: {path}")
    with open(path, "rb") as f:
        return pickle.load(f)


def artifact_exists(name: str) -> bool:
    return (MODELS_DIR / f"{name}.pkl").exists()


# ─── Evaluation Helpers ────────────────────────────────────────────────────────

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def evaluate_classifier(
    y_true: List,
    y_pred: List,
    y_proba: Optional[np.ndarray] = None,
    labels: Optional[List[str]] = None,
) -> Dict[str, Any]:
    report = {
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "f1_macro": round(f1_score(y_true, y_pred, average="macro", zero_division=0), 4),
        "f1_weighted": round(f1_score(y_true, y_pred, average="weighted", zero_division=0), 4),
        "precision_macro": round(precision_score(y_true, y_pred, average="macro", zero_division=0), 4),
        "recall_macro": round(recall_score(y_true, y_pred, average="macro", zero_division=0), 4),
        "classification_report": classification_report(y_true, y_pred, target_names=labels, zero_division=0),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
    }
    if y_proba is not None:
        try:
            n_classes = y_proba.shape[1] if y_proba.ndim > 1 else 2
            multi = "ovr" if n_classes > 2 else "raise"
            report["roc_auc"] = round(
                roc_auc_score(y_true, y_proba if n_classes > 2 else y_proba[:, 1],
                              multi_class=multi, average="macro"), 4
            )
        except Exception:
            pass
    return report


# ─── FastAPI Health Helper ─────────────────────────────────────────────────────

def build_health_response(service: str, version: str, ready: bool) -> Dict[str, Any]:
    return {
        "service": service,
        "version": version,
        "status": "healthy" if ready else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics.summary(),
    }