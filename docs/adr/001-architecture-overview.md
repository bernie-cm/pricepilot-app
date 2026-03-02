# ADR-001: Core Architecture Decisions

## Status
Accepted

## Context
Price Pilot is a grocery price aggregation platform for Australian supermarkets.
We are building it as a learning project to develop practical DevOps and
Kubernetes skills while producing a production-grade application.

This ADR records the foundational decisions made during the planning phase before
any application code was written.

---

## Decisions

### 1. Language: Python 3.12

**Decision:** Python for all backend services.

**Reasoning:** The developer is already proficient in Python. The goal of this
project is to learn DevOps and Kubernetes — not a new programming language. Using
a familiar language keeps the learning focus where it belongs. Python also has a
strong ecosystem for the two main requirements: web scraping (Playwright, httpx)
and REST APIs (FastAPI).

**Alternatives considered:** Go — rejected because it would require learning a
new language in parallel with Kubernetes and AWS, splitting focus.

---

### 2. API Framework: FastAPI

**Decision:** FastAPI for all REST services.

**Reasoning:** Async-native, which pairs well with I/O-heavy operations (database
queries, HTTP calls to supermarket APIs). Generates OpenAPI docs automatically.
Pydantic validation is built in, reducing boilerplate. It is the modern standard
for Python APIs.

**Alternatives considered:** Django REST Framework — more batteries-included but
heavier; Flask — simpler but lacks async-native support and automatic validation.

---

### 3. Message Queue: RabbitMQ over Kafka

**Decision:** RabbitMQ for the scraper → processor pipeline.

**Reasoning:** Scrapers run once daily and publish thousands of product records.
RabbitMQ handles this with ease and runs comfortably as a single pod. Kafka is
designed for millions of events per second, requires minimum 3 brokers for
production, and carries significant operational overhead — none of which is
justified by our workload.

**Alternatives considered:** Kafka — rejected as over-engineered for our volume.
Redis Streams — viable but less explicit about queue semantics; RabbitMQ has
clearer dead-letter and retry behaviour which we will use for scraper failures.

---

### 4. Local Kubernetes: k3d

**Decision:** k3d (k3s running in Docker) for local Kubernetes development.

**Reasoning:** k3d starts fast, uses minimal memory, supports multi-node clusters,
and includes Traefik ingress by default. It runs entirely in Docker so there is
no VM overhead.

**Alternatives considered:**
- minikube — heavier (VM-based), slower startup; valid alternative if already installed
- kind — excellent for CI but slightly less feature-rich for local dev
- All three expose the same Kubernetes API; the choice does not affect how K8s
  concepts are learned

---

### 5. Cloud Provider: AWS

**Decision:** AWS for all production infrastructure.

**Reasoning:** Developer already has an AWS account and familiarity with AWS
fundamentals. AWS is the most common cloud provider in industry.

**AWS services selected:**

| Need | Service |
|---|---|
| Kubernetes | EKS (managed control plane) |
| Container registry | ECR |
| PostgreSQL | RDS |
| Redis | ElastiCache |
| DNS | Route 53 |
| TLS certificates | ACM |
| Ingress | AWS Load Balancer Controller + ALB |
| Secrets | AWS Secrets Manager + External Secrets Operator |
| IaC state | S3 + DynamoDB lock table |
| Node autoscaling | Karpenter |
| CDN | CloudFront |

---

### 6. GitOps and Deployment Strategy

**Decision:** ArgoCD for GitOps; GitHub Actions for CI.

**Reasoning:** ArgoCD watches the Git repository and keeps the cluster in sync
with what is declared in Helm charts. This means the cluster state is always
reproducible from Git — a core DevOps principle. GitHub Actions handles
building, testing, and pushing images; ArgoCD handles deploying them.

**Deployment pipeline:**
```
dev     → automatic (ArgoCD syncs on merge to main)
staging → manual trigger (developer presses sync)
prod    → manual trigger with GitHub Environment approval gate
```

---

### 7. Observability Stack

**Decision:** Prometheus + Grafana (metrics), Loki (logs), Tempo (traces),
all instrumented via OpenTelemetry.

**Reasoning:** Industry-standard open-source stack with no vendor lock-in.
Deployed via the `kube-prometheus-stack` Helm chart which provisions the full
metrics stack in one command. OpenTelemetry provides vendor-neutral
instrumentation so the backend can change without touching application code.

---

## Consequences

- Services must be written as async Python (asyncio / FastAPI) to work well with
  the chosen stack
- Each service manages its own `pyproject.toml` and dependencies (no shared
  root-level Python environment)
- RabbitMQ must be included in local docker-compose and as a K8s Deployment
- Infrastructure changes require Terraform plan review before apply
- EKS control plane costs ~$72/month — the cluster should be torn down between
  active development sessions to control cost
