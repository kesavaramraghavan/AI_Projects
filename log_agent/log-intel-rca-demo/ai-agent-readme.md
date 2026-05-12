# AI Agent & RCA pipeline - internals, usage, and troubleshooting

This document covers how the RCA pipeline in `retrieval-api` works, how to configure and test it, and how to use it to investigate incidents in the demo environment. It also covers the optional OpenRouter/LLM integration.

---

## Architecture overview

The `retrieval-api` service (FastAPI) exposes two endpoints backed by Elasticsearch queries:

**`POST /search/logs`** - General keyword and filter search against the `logs-demo` index. Accepts a text query, optional service name filter, and a `minutes_back` window. Returns matching log documents ordered by timestamp descending.

**`POST /search/rca`** - Heuristic root-cause analysis. Takes a natural-language question and a time window, then internally queries Elasticsearch for recent events matching `error` or `timeout`, aggregates them by `service` and `error_class`, and returns a ranked list of hypotheses. Each hypothesis includes a short title, the supporting evidence (top service, top error class, event count), and a list of suggested next steps.

The RCA logic is deterministic - it does not call any external service by default. This makes it fast and predictable, and appropriate for a day-one investigation when you want to narrow down which service and error type to focus on. The hypotheses it generates are based entirely on log volume and grouping, not semantic understanding, so treat them as a starting point rather than a conclusion.

If `OPENROUTER_API_KEY` is set in the environment, the service will additionally call an LLM through OpenRouter and return a more structured analysis. If that call fails, it falls back to the heuristic result.

---

## Starting and verifying the service

The `retrieval-api` is part of the main compose stack. If the full stack is already running, the service should already be up. To start or rebuild it individually:

```bash
cd ~/log-intel-rca-demo
docker compose up -d --build retrieval-api
docker compose ps retrieval-api
```

Confirm it is accepting connections:

```bash
curl -I http://127.0.0.1:8000/docs
```

Expected: `HTTP/1.1 200 OK`

---

## Testing the endpoints

**Log search** - retrieve error events from the last hour:

```bash
curl -sS -X POST http://127.0.0.1:8000/search/logs \
  -H "Content-Type: application/json" \
  -d '{"text": "timeout", "minutes_back": 60}' | jq .
```

**RCA query** - analyze why a service may have failed:

```bash
curl -sS -X POST http://127.0.0.1:8000/search/rca \
  -H "Content-Type: application/json" \
  -d '{"question": "why did checkout fail", "minutes_back": 60}' | jq .
```

A well-formed RCA response looks roughly like:

```json
{
  "hypotheses": [
    {
      "title": "checkout-api produced the most errors in the window",
      "evidence": {
        "service": "checkout-api",
        "error_class": "TimeoutError",
        "count": 47
      },
      "next_steps": [
        "Check checkout-api logs around the incident window",
        "Search for correlated errors in inventory-service using the same trace_id",
        "Verify recent deployments to checkout-api"
      ]
    }
  ]
}
```

If the response is empty or returns zero hypotheses, either no error/timeout events exist in the requested time window or Elasticsearch is not reachable. Run the log count check:

```bash
curl -s http://127.0.0.1:9200/logs-demo/_count | jq .
```

---

## CORS configuration (required if the UI calls the API from the browser)

By default, browsers block cross-origin requests unless the server explicitly allows them. If you are serving the web UI from a different origin than the API, add CORS middleware to `services/retrieval-api/app.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Restrict to specific origins in any environment you care about
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Rebuild after the change:

```bash
docker compose up -d --build retrieval-api
```

---

## Using the RCA endpoint for incident investigation

The intended workflow is:

1. **Trigger an RCA query** against the time window containing the incident. Use the UI or call the endpoint directly with `minutes_back` set to cover the relevant period.

2. **Identify the top hypothesis.** The response ranks services by error volume in that window. The top entry is where to look first - not because it is necessarily the root cause, but because it is where the most signal is.

3. **Drill into the identified service** using targeted log searches:

   ```bash
   # Narrow to a specific service and error type
   curl -sS -X POST http://127.0.0.1:8000/search/logs \
     -H "Content-Type: application/json" \
     -d '{"text": "TimeoutError", "service": "checkout-api", "minutes_back": 60}' | jq .
   ```

4. **Check the container's own logs** for stack traces or configuration errors that may not be captured in the structured log events:

   ```bash
   docker compose logs checkout-api --tail 200
   ```

5. **Check dependencies.** If the hypothesis points to a service that depends on another (e.g. `checkout-api` calling `inventory-service`), search for correlated errors in the dependency using a `trace_id` from the evidence:

   ```bash
   curl -sS -X POST http://127.0.0.1:8000/search/logs \
     -H "Content-Type: application/json" \
     -d '{"text": "<trace_id>", "minutes_back": 60}' | jq .
   ```

6. **Check host-level resources** if log patterns suggest resource exhaustion:

   ```bash
   df -h          # disk
   free -h        # memory
   top -b -n 1 | head -n 25   # CPU and process summary
   ```

---

## OpenRouter / LLM integration

When `OPENROUTER_API_KEY` is present, the RCA endpoint sends a structured prompt to an LLM via OpenRouter and returns the model's output alongside or in place of the heuristic result. This produces more natural hypotheses and can surface patterns the aggregation-based heuristic misses.

### Setup

1. Copy the example environment file and add your key:

   ```bash
   cd ~/log-intel-rca-demo
   cp .env.example .env
   ```

   Edit `.env` and set:

   ```env
   OPENROUTER_API_KEY=<your-key>
   OPENROUTER_MODEL=nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free
   ```

2. Rebuild the API so it picks up the environment variables:

   ```bash
   docker compose up -d --build retrieval-api
   ```

3. Test the LLM-backed endpoint:

   ```bash
   curl -sS -X POST http://127.0.0.1:8000/search/rca \
     -H "Content-Type: application/json" \
     -d '{"question": "why did checkout fail", "minutes_back": 60}' | jq .
   ```

### Behavior notes

- The API expects the model to return valid JSON. If the response cannot be parsed, the service logs the error and returns the heuristic result instead.
- The fallback means the endpoint will not return a 500 if the LLM call fails - but it also means a bad API key or quota exhaustion will silently fall back without surfacing an obvious error to the caller. Check the `retrieval-api` container logs if responses look like they are coming from the heuristic when you expect LLM output:

  ```bash
  docker compose logs retrieval-api --tail 100
  ```

- Do not commit `.env` to version control. The `.gitignore` should already exclude it; verify this before pushing.

---

## Common errors and fixes

### "Connection refused" when the consumer tries to reach Elasticsearch

**Cause:** The Elasticsearch container has exited or has not finished initializing.

**Check:**

```bash
docker compose ps elasticsearch
docker compose logs elasticsearch --tail 200
```

Common log indicators:

- `max virtual memory areas vm.max_map_count [65530] is too low` → set `vm.max_map_count=262144` on the host (see below)
- `java.lang.OutOfMemoryError` → reduce `ES_JAVA_OPTS` heap in `docker-compose.yml`

**Fix for vm.max_map_count:**

```bash
sudo sysctl -w vm.max_map_count=262144
echo 'vm.max_map_count=262144' | sudo tee -a /etc/sysctl.conf
docker compose restart elasticsearch
```

**Fix for heap:**

In `docker-compose.yml`, under the `elasticsearch` service:

```yaml
environment:
  - ES_JAVA_OPTS=-Xms512m -Xmx512m
```

Then:

```bash
docker compose down
docker compose up -d --build
```

### API responds on localhost but is unreachable from the browser

**Cause:** EC2 security group or UFW is blocking the port.

**Steps:**

1. Confirm the API is actually listening on the VM:

   ```bash
   curl -I http://127.0.0.1:8000/docs   # should return 200
   ss -ltnp | grep 8000                  # should show a listening socket
   ```

2. Check UFW:

   ```bash
   sudo ufw status
   ```

3. Check the EC2 security group in the AWS console - inbound TCP 8000 and 8080 must be allowed from your IP.

### "Bad permissions" / SSH refuses to use the private key (Windows)

**Cause:** OpenSSH rejects private keys that are readable by users other than the owner.

**Fix:**

```powershell
takeown /f .\aws-ec2-key
icacls .\aws-ec2-key /inheritance:r
icacls .\aws-ec2-key /grant:r "%USERDOMAIN%\%USERNAME%:R"
```

Run from the directory containing the private key file. Elevate PowerShell if `takeown` fails with an access error.

### Build error: "unable to prepare context: path not found"

**Cause:** The `services/` directory is missing on the VM. Docker cannot find the build context for one or more services.

**Fix:** Re-copy or re-clone the full project directory. Confirm `services/log-generator`, `services/kafka-consumer`, and `services/retrieval-api` all exist on the VM before running `docker compose up --build`.

---

## Escalation - what to collect

When handing off an incident or filing a bug report, capture the following:

```bash
# Container state
docker compose ps --all

# Logs from relevant services (adjust service names as needed)
docker compose logs kafka-consumer --tail 500
docker compose logs retrieval-api --tail 500
docker compose logs elasticsearch --tail 500

# Elasticsearch index health and document count
curl -s http://127.0.0.1:9200/_cat/indices?v
curl -s http://127.0.0.1:9200/logs-demo/_count

# Sample log search for the error in question
curl -sS -X POST http://127.0.0.1:8000/search/logs \
  -H "Content-Type: application/json" \
  -d '{"text": "<error text>", "minutes_back": 60}'

# Host resource state
df -h
free -h
ss -ltnp
```

---

## Planned improvements

The following extensions are not yet implemented but represent the natural next steps for this pipeline:

- **LLM-backed RCA with structured output** - replace the heuristic grouping with a prompt that asks the model to return JSON with hypothesis titles, confidence levels, evidence pointers (trace IDs or document IDs), and recommended actions. The current OpenRouter integration is a partial step toward this.

- **Embedding-based similarity search** - embed log event text and store vectors in Elasticsearch's dense vector field. This would allow the RCA endpoint to retrieve historically similar incidents rather than relying purely on keyword matches and aggregations.

- **Automated runbooks** - expose additional API endpoints that perform common remediation actions (restart a container, flush an index, increase a JVM heap setting via config update) so the UI can offer one-click responses to well-understood failure modes.
