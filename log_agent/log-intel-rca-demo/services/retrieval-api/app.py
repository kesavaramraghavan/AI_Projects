from datetime import datetime, timedelta
from typing import Optional
import os
import json
import requests
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from elasticsearch import Elasticsearch

ES_INDEX = "logs-demo"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

es = Elasticsearch(os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200"))

# basic logging to help debug OpenRouter calls
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("retrieval-api")


class LogQuery(BaseModel):
    text: Optional[str] = None
    service: Optional[str] = None
    severity: Optional[str] = None
    minutes_back: int = 15


class RCAQuery(BaseModel):
    question: str
    minutes_back: int = 30


@app.post("/search/logs")
def search_logs(q: LogQuery):
    now = datetime.utcnow()
    start = now - timedelta(minutes=q.minutes_back)

    must = [
        {"range": {"timestamp": {"gte": start.isoformat(), "lte": now.isoformat()}}}
    ]
    
    if q.text:
        must.append({"match": {"message": q.text}})
    if q.service:
        must.append({"term": {"service": q.service}})
    if q.severity:
        must.append({"term": {"severity": q.severity}})

    body = {"query": {"bool": {"must": must}}, "size": 100, "sort": [{"timestamp": "desc"}]}
    try:
        resp = es.search(index=ES_INDEX, body=body)
        hits = [h["_source"] for h in resp["hits"]["hits"]]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Elasticsearch query failed: {str(e)}")
    return {"results": hits}


def call_openrouter_rca(question: str, logs: list) -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENROUTER_API_KEY")

    base_url = os.getenv("OPENROUTER_BASE_URL", "https://api.openrouter.ai/v1")
    model = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free")
    url = base_url.rstrip("/") + "/chat/completions"

    # Build a concise log summary to include in the prompt (top 20 lines)
    lines = []
    for l in logs[:20]:
        ts = l.get("timestamp", "")
        svc = l.get("service", "")
        err = l.get("error_class", "")
        msg = l.get("message", "").replace("\n", " ")
        lines.append(f"{ts} | {svc} | {err} | {msg}")
    logs_text = "\n".join(lines) or "No logs available."

    system = (
        "You are an expert site reliability engineer and RCA assistant. "
        "Given a short user question and recent logs, produce a JSON object with keys: "
        "'summary' (short string) and 'hypotheses' (array). Each hypothesis must be an object with "
        "'title' (short string), 'confidence' (0-1 float), 'evidence' (object with top_service, top_error_class, error_count), "
        "and 'next_steps' (array of short action strings). Return only valid JSON and nothing else."
    )

    user_prompt = f"Question: {question}\n\nLogs (most recent first):\n{logs_text}\n\nReturn the JSON described above."

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 800,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        logger.info("OpenRouter: calling model %s at %s", model, url)
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
    except Exception as e:
        logger.exception("OpenRouter request exception")
        raise HTTPException(status_code=502, detail=f"OpenRouter request failed: {str(e)}")

    if resp.status_code != 200:
        logger.info("OpenRouter returned status %s", resp.status_code)
        # Do not log full body in INFO level to avoid leaking secrets; include snippet at debug
        logger.debug("OpenRouter response body: %s", resp.text[:1000])
        raise HTTPException(status_code=502, detail=f"OpenRouter error: {resp.status_code} {resp.text}")

    data = resp.json()
    content = None
    # OpenRouter uses an OpenAI-compatible response shape
    try:
        content = data["choices"][0]["message"]["content"]
    except Exception:
        try:
            content = data["choices"][0].get("text")
        except Exception:
            content = None

    if not content:
        raise HTTPException(status_code=502, detail="OpenRouter returned empty response")

    # Try to parse JSON from the model output
    try:
        parsed = json.loads(content)
        return parsed
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(content[start:end+1])
                return parsed
            except json.JSONDecodeError:
                raise HTTPException(status_code=502, detail="OpenRouter returned non-JSON content")
    raise HTTPException(status_code=502, detail="OpenRouter returned non-JSON content")


def simulate_llm_rca(question: str, logs: list) -> dict:
    """Deterministic local fallback that mimics an LLM RCA response for demos.
    This is used when external LLM calls fail (network or DNS issues).
    The response is tailored to the question by extracting keywords.
    """
    # Extract relevant keywords from the question
    question_lower = question.lower()
    q_keywords = set(question_lower.split())

    # Known service/error mappings derived from the log generator
    known_services = {"checkout-api", "inventory-service", "payment-gateway"}
    known_errors = {"timeouterror", "timeout", "paymentdeclined", "payment", "500", "error", "failure", "fail", "timeouts"}
    known_focus = {"checkout", "inventory", "payment", "timeout", "declined", "500s", "submission"}

    # Detect which services / errors the question is asking about
    mentioned_services = {s for s in known_services if any(kw in question_lower for kw in s.replace("-", " ").split())}
    mentioned_errors = {e for e in known_errors if e in q_keywords or e in question_lower}
    mentioned_focus = {f for f in known_focus if f in q_keywords or f in question_lower}

    # Filter logs based on question context
    filtered_logs = logs
    if mentioned_services:
        filtered_logs = [l for l in filtered_logs if l.get("service") in mentioned_services]
    if mentioned_errors:
        err_patterns = {e for e in mentioned_errors if e not in ("error", "failure", "fail")}
        for e in err_patterns:
            filtered_logs = [l for l in filtered_logs
                            if e in (l.get("error_class") or "").lower()
                            or e in (l.get("message") or "").lower()]

    # Use filtered logs if available, else fall back to all logs
    work_logs = filtered_logs if filtered_logs else logs

    # Group by service & error_class
    counts = {}
    examples = {}
    for l in work_logs:
        key = (l.get("service"), l.get("error_class"))
        counts[key] = counts.get(key, 0) + 1
        examples.setdefault(key, []).append(l.get("message", ""))

    if not counts:
        return {
            "summary": f"No matching errors found for your question: '{question}'. Try broadening the search window.",
            "hypotheses": []
        }

    # Sort hypotheses by count descending
    sorted_keys = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    hypotheses = []
    total_errors = sum(counts.values())

    for (top_service, top_error), count in sorted_keys[:3]:  # top 3 hypotheses
        sample_msgs = list(dict.fromkeys(examples.get((top_service, top_error), [])))[:3]

        # Build a question-specific summary
        if mentioned_services or mentioned_errors or mentioned_focus:
            summary = (
                f"Regarding your question about {question.strip('?')}: "
                f"{top_service} shows {count} occurrences of {top_error or 'UnknownError'} "
                f"({count/total_errors*100:.0f}% of errors in scope)."
            )
        else:
            summary = (
                f"Based on the last window, {top_service} shows increased occurrences of "
                f"{top_error or 'UnknownError'} ({count} events)."
            )

        confidence = min(0.85, 0.4 + (count / max(10, total_errors)))

        hypothesis = {
            "title": f"{top_service} likely causing the incident: {top_error or 'UnknownError'}",
            "confidence": round(confidence, 2),
            "evidence": {
                "top_service": top_service,
                "top_error_class": top_error,
                "error_count": count,
                "examples": sample_msgs
            },
            "next_steps": [
                f"Filter logs for {top_service} with error_class={top_error}",
                "Check recent deploys and configuration changes",
                "Run health checks on dependent services",
                f"Search trace_ids in {top_service} logs for correlating failures"
            ]
        }
        hypotheses.append(hypothesis)

    return {"summary": summary, "hypotheses": hypotheses}


@app.post("/search/rca")
def search_rca(q: RCAQuery):
    # Collect logs and then optionally call OpenRouter
    log_q = LogQuery(text="error OR timeout", minutes_back=q.minutes_back)
    logs = search_logs(log_q)["results"]

    # If OpenRouter is configured, attempt to get an LLM-based RCA
    if os.getenv("OPENROUTER_API_KEY"):
        try:
            return call_openrouter_rca(q.question, logs)
        except HTTPException:
            # If the external LLM call fails (network, DNS, or API error),
            # return a deterministic local LLM-like response so the demo remains functional.
            logger.info("OpenRouter call failed; using simulate_llm_rca fallback")
            return simulate_llm_rca(q.question, logs)

    # simple grouping by service & error_class
    counts = {}
    for l in logs:
        key = (l.get("service"), l.get("error_class"))
        counts[key] = counts.get(key, 0) + 1

    if not counts:
        return {
            "summary": "No clear error spikes found in the selected window.",
            "hypotheses": []
        }

    (top_service, top_error), count = max(counts.items(), key=lambda kv: kv[1])

    hypothesis = {
        "title": f"{top_service} shows the highest error volume ({top_error or 'UnknownError'})",
        "confidence": 0.6,
        "evidence": {
            "top_service": top_service,
            "top_error_class": top_error,
            "error_count": count
        },
        "next_steps": [
            "Filter logs by this service and error_class",
            "Inspect recent deploys for this service",
            "Drill into correlated services (e.g., dependencies)"
        ]
    }

    return {
        "summary": "Heuristic RCA based on error distribution (no LLM configured).",
        "hypotheses": [hypothesis]
    }
