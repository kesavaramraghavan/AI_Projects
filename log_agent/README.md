# Log Intelligence & RCA Demo

This repository contains a self-contained demo stack that generates synthetic application logs, ingests them through Kafka into Elasticsearch, and exposes a FastAPI service with keyword search and heuristic root-cause analysis (RCA) endpoints. A minimal browser UI sits in front of the API.

The goal is to have a working end-to-end log intelligence pipeline you can run on a single EC2 instance, inspect, and extend - either by wiring in a real log source or by swapping the heuristic RCA handler for an LLM call.

---

## How the stack fits together

```
log-generator  →  Kafka (logs.raw topic)  →  kafka-consumer  →  Elasticsearch (logs-demo index)
                                                                          ↑
                                                               retrieval-api (FastAPI)
                                                                          ↑
                                                                  web UI (static)
```

**log-generator** - Python service that emits structured JSON log events at a configurable rate. Writes to the `logs.raw` Kafka topic. Produces a mix of INFO, WARN, and ERROR events across several synthetic service names so the RCA endpoint has something realistic to work with.

**kafka-consumer** - Reads from `logs.raw`, normalizes the event schema, and indexes documents into the `logs-demo` Elasticsearch index. Running Kafka between the generator and the indexer decouples ingestion from indexing and makes it straightforward to swap in a real log source later.

**retrieval-api** - FastAPI application with two endpoints:

- `POST /search/logs` - keyword and filter search against `logs-demo`.
- `POST /search/rca` - heuristic RCA that queries recent error and timeout events, groups them by service and error class, and returns a ranked list of hypotheses with evidence and suggested next steps.

**web** - Static HTML/JS/CSS UI that calls the API and renders results in the browser. No build step; served via a lightweight HTTP server container.

**Elasticsearch + Kibana** - Storage and optional visualization. Kibana is included in the compose file but is not required for the RCA flow.

**Zookeeper + Kafka** - Standard Kafka broker setup. Zookeeper is required for the Kafka version used here.

---

## Repository layout

```
.
├── docker-compose.yml          # Full stack definition
├── services/
│   ├── log-generator/          # Synthetic log producer
│   ├── kafka-consumer/         # ES indexer
│   └── retrieval-api/          # FastAPI search + RCA service
├── web/                        # Browser UI (index.html, app.js, styles.css)
└── terraform/                  # EC2 provisioning
    ├── main.tf
    ├── variables.tf
    └── terraform-readme.md     # Infrastructure setup guide
```

---

## Quick start

These steps assume you have already provisioned the EC2 VM. If you have not, see [`terraform/terraform-readme.md`](terraform/terraform-readme.md) first.

**1. SSH into the VM**

```bash
ssh -i ~/.ssh/aws-ec2-key ubuntu@<VM_PUBLIC_IP>
```

**2. Start the stack**

```bash
cd ~/log-intel-rca-demo
docker compose pull
docker compose up -d --build
```

**3. Verify containers are running**

```bash
docker compose ps
```

All services should show `Up`. If any container has exited, check its logs before proceeding:

```bash
docker compose logs <service-name> --tail 200
```

**4. Confirm the API is responding**

```bash
curl -I http://127.0.0.1:8000/docs
```

Expected: `HTTP/1.1 200 OK`

**5. Access from your workstation**

| Endpoint     | URL                               |
| ------------ | --------------------------------- |
| Web UI       | `http://<VM_PUBLIC_IP>:8080`      |
| FastAPI docs | `http://<VM_PUBLIC_IP>:8000/docs` |
| Kibana       | `http://<VM_PUBLIC_IP>:5601`      |

If the UI or API is unreachable from outside the VM, verify that the EC2 security group has inbound rules open for ports 8000 and 8080 from your IP. See the troubleshooting section in [`terraform/terraform-readme.md`](terraform/terraform-readme.md).

---

## Verifying data flow

Once the stack is up, confirm that logs are flowing end-to-end before testing the RCA endpoint.

Check that the Elasticsearch index has documents:

```bash
curl -s http://127.0.0.1:9200/logs-demo/_count | jq .
```

Expected: `"count"` is greater than 0 after a minute or two.

Run a test search:

```bash
curl -sS -X POST http://127.0.0.1:8000/search/logs \
  -H "Content-Type: application/json" \
  -d '{"text": "error", "minutes_back": 60}' | jq .
```

Run a test RCA query:

```bash
curl -sS -X POST http://127.0.0.1:8000/search/rca \
  -H "Content-Type: application/json" \
  -d '{"question": "why did checkout fail", "minutes_back": 60}' | jq .
```

---

## First-line troubleshooting

**Nothing in Elasticsearch / kafka-consumer keeps restarting**

Kafka takes 15–30 seconds to be ready. The consumer may have started before the broker was accepting connections and exited. Restart it:

```bash
docker compose restart kafka-consumer
docker compose logs kafka-consumer --tail 100
```

**Elasticsearch exits immediately**

Almost always a `vm.max_map_count` issue. Set it on the host:

```bash
sudo sysctl -w vm.max_map_count=262144
echo 'vm.max_map_count=262144' | sudo tee -a /etc/sysctl.conf
```

Then restart Elasticsearch:

```bash
docker compose restart elasticsearch
```

If the instance has less than 4 GB RAM, also reduce the ES heap in `docker-compose.yml`:

```yaml
environment:
  - ES_JAVA_OPTS=-Xms512m -Xmx512m
```

**Build fails: "path not found" for a service context**

The `services/` directory is missing on the VM. SCP or clone the full project directory rather than a subset of files.

**API responds locally but not from the browser**

Check EC2 security group inbound rules (ports 8000, 8080) and confirm UFW on the VM is not blocking:

```bash
sudo ufw status
```

For more detailed troubleshooting of the RCA pipeline and AI agent configuration, see [`log-intel-rca-demo/ai-agent-readme.md`](log-intel-rca-demo/ai-agent-readme.md).

---

## Related documentation

- [`terraform/terraform-readme.md`](terraform/terraform-readme.md) - Provisioning the EC2 VM, SSH access, Docker installation, and infrastructure teardown.
- [`log-intel-rca-demo/ai-agent-readme.md`](log-intel-rca-demo/ai-agent-readme.md) - RCA endpoint internals, OpenRouter/LLM integration, diagnostic workflows, and escalation procedures.
