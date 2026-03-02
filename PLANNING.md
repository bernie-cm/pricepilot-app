# Price Pilot — Architecture & Planning

> A grocery price aggregation platform for Australian supermarkets, designed as a
> production-grade, Kubernetes-native application.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Functional Requirements](#2-functional-requirements)
3. [Non-Functional Requirements](#3-non-functional-requirements)
4. [System Architecture](#4-system-architecture)
5. [Service Breakdown](#5-service-breakdown)
6. [Data Model (Conceptual)](#6-data-model-conceptual)
7. [Tech Stack Recommendations](#7-tech-stack-recommendations)
8. [DevOps & Kubernetes Strategy](#8-devops--kubernetes-strategy)
9. [Technical Risks & Mitigations](#9-technical-risks--mitigations)
10. [Phased Roadmap](#10-phased-roadmap)
11. [Open Questions](#11-open-questions)

---

## 1. Project Overview

**Price Pilot** aggregates grocery prices from major Australian supermarkets
(Woolworths, Coles, and optionally ALDI/IGA) so users can compare prices, build
shopping lists, and receive daily digest emails showing where to get the best
deals.

Two primary personas (from the C4 diagram):

| Persona | Core need |
|---|---|
| **User** | Browse/search products, build a shopping list, see lowest price across stores, get a daily email |
| **Administrator** | Manage users, trigger manual scraper runs, monitor system health |

---

## 2. Functional Requirements

### User-facing
- [ ] Search for grocery products by name or category
- [ ] View current price at each available supermarket
- [ ] See price history charts per product
- [ ] Create and manage a personal shopping list
- [ ] Get a daily email digest with shopping list prices and cheapest store
- [ ] Filter/sort results by store, price, distance (future)
- [ ] User authentication (sign up, login, password reset)

### Admin-facing
- [ ] Admin dashboard: view users, manage accounts
- [ ] Trigger a manual scraper run per store
- [ ] View scraper logs and health metrics
- [ ] Configure scrape schedules without redeployment

### System behaviour
- [ ] Prices refresh at least once per day (configurable per store)
- [ ] Stale prices are clearly flagged to users (e.g., > 24 h old)
- [ ] Email notifications sent via Mailgun once per day per user

---

## 3. Non-Functional Requirements

| Concern | Target |
|---|---|
| **Availability** | 99.5 % uptime for the API and frontend |
| **Freshness** | Prices no older than 24 h under normal operation |
| **Latency** | Product search API < 200 ms p95 |
| **Scalability** | Scraper jobs scale independently of the user-facing API |
| **Observability** | Logs, metrics, and traces for every service |
| **Security** | No credentials in source control; secrets via K8s Secrets / Vault |
| **Compliance** | Australian Privacy Act (handling personal data/email addresses) |

---

## 4. System Architecture

### 4.1 C4 Container Level (expansion of the existing context diagram)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Kubernetes Cluster                           │
│                                                                     │
│  ┌──────────────┐   ┌─────────────────┐   ┌────────────────────┐  │
│  │   Frontend   │   │   API Gateway   │   │   Admin Dashboard  │  │
│  │  (Next.js)   │──▶│  (nginx-ingress │   │    (Next.js or     │  │
│  │              │   │   + rate limit) │   │     Grafana)       │  │
│  └──────────────┘   └────────┬────────┘   └────────────────────┘  │
│                              │                                      │
│          ┌───────────────────┼────────────────────┐                │
│          ▼                   ▼                    ▼                │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐    │
│  │  User Service│  │  Product/Price   │  │    Notifier      │    │
│  │  (auth,      │  │  Service (query  │  │    Service       │    │
│  │  profiles,   │  │  + history API)  │  │  (email digest)  │    │
│  │  lists)      │  │                  │  │                  │    │
│  └──────┬───────┘  └────────┬─────────┘  └──────┬───────────┘    │
│         │                   │                    │                  │
│         └───────────────────┼────────────────────┘                │
│                             ▼                                       │
│                    ┌────────────────┐                              │
│                    │  Message Queue │                              │
│                    │  (RabbitMQ)    │                              │
│                    └───────┬────────┘                              │
│                            │                                        │
│          ┌─────────────────┼──────────────────┐                   │
│          ▼                 ▼                  ▼                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐          │
│  │  Woolworths  │ │    Coles     │ │   (Future store) │          │
│  │   Scraper   │ │   Scraper    │ │     Scraper      │          │
│  │  (CronJob)  │ │  (CronJob)   │ │    (CronJob)     │          │
│  └──────────────┘ └──────────────┘ └──────────────────┘          │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                      Data Layer                               │ │
│  │  ┌──────────────────┐         ┌──────────────────┐           │ │
│  │  │   PostgreSQL      │         │      Redis       │           │ │
│  │  │  (products,       │         │  (cache, rate    │           │ │
│  │  │   prices, users,  │         │   limiting,      │           │ │
│  │  │   lists)          │         │   session)       │           │ │
│  │  └──────────────────┘         └──────────────────┘           │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘

External Systems
  ├── Woolworths website / internal API
  ├── Coles website / internal API
  └── Mailgun (transactional email)
```

### 4.2 Data Flow: Price Scrape Cycle

```
1. K8s CronJob triggers Scraper (e.g., 02:00 AEST daily)
2. Scraper fetches product catalogue and prices from store website
3. Raw data published to RabbitMQ queue `prices.raw`
4. Price Processor (consumer) normalises, deduplicates, stores in PostgreSQL
5. Redis cache invalidated for affected product IDs
6. Notifier queries cheapest prices per shopping list → Mailgun → User inbox
```

---

## 5. Service Breakdown

### 5.1 Scraper Services (one per store)

**Responsibility:** Fetch raw product and price data from a supermarket.

- Runs as a **Kubernetes CronJob** (scheduled, not always running — cost-efficient)
- Each store gets its own container image (different scraping logic)
- Publishes raw JSON to RabbitMQ; does NOT write to the database directly
- Stateless — safe to retry, kill, and restart

**Key decision — scraping approach:**

| Approach | Pros | Cons |
|---|---|---|
| Reverse-engineered internal API | Fast, structured data | May break without notice; ToS grey area |
| HTML scraping (Playwright) | Works even with JS-rendered pages | Slower, brittle to UI changes, heavier resource usage |
| Hybrid | Best coverage | More maintenance |

> **Recommended start:** Reverse-engineer the internal REST APIs that the
> Woolworths and Coles mobile apps use. These return clean JSON and are far more
> stable than HTML scraping. Tools like mitmproxy or Charles Proxy can capture
> them. Accept that these may change and build a clear alerting strategy for
> failures.

### 5.2 Price Processor / Product Service

**Responsibility:** Consume raw scrape data, normalise it, and expose a query API.

- Consumes from RabbitMQ
- Upserts products and prices into PostgreSQL
- Exposes REST (or GraphQL) API for product search and price history
- Backed by Redis cache for frequently searched products

### 5.3 User Service

**Responsibility:** Authentication, user profiles, shopping list management.

- JWT-based auth (access + refresh tokens)
- CRUD for shopping lists (list of product IDs with quantity)
- Stores data in PostgreSQL (separate schema or database from price data)

### 5.4 Notifier Service

**Responsibility:** Daily email digest.

- Triggered by a K8s CronJob (e.g., 07:00 AEST)
- Queries User Service for active shopping lists
- Queries Product Service for latest prices
- Computes cheapest-store recommendation per list
- Sends via Mailgun API
- Idempotent — if re-run same day, skips already-notified users

### 5.5 Frontend (Next.js)

**Responsibility:** User-facing web UI.

- Server-side rendering for SEO and fast initial load
- Communicates with API Gateway only (never directly to internal services)
- Static assets served via CDN (AWS CloudFront)

### 5.6 API Gateway / Ingress

**Responsibility:** Single entry point; TLS termination, routing, rate limiting.

- Kubernetes nginx-ingress controller
- Rate limiting per IP to reduce scraping of Price Pilot itself
- TLS via cert-manager + Let's Encrypt

---

## 6. Data Model (Conceptual)

```
products
  id, name, brand, category, unit, unit_size, barcode, image_url, created_at

store_products
  id, product_id, store (woolworths|coles|aldi), store_product_id,
  name_at_store, url, last_scraped_at

prices
  id, store_product_id, price_cents, was_price_cents, is_on_special,
  scraped_at

users
  id, email, password_hash, created_at, email_verified_at

shopping_lists
  id, user_id, name, created_at

shopping_list_items
  id, shopping_list_id, product_id, quantity

notification_log
  id, user_id, sent_at, status
```

**Product matching** (linking the same physical product across stores) is one of
the hardest problems. Initial strategy: match by barcode where available, then
fuzzy-match on brand + name + unit size with a manual review queue for ambiguous
cases.

---

## 7. Tech Stack Recommendations

| Layer | Choice | Rationale |
|---|---|---|
| **Language — backends** | **Go** (primary) | Small binaries, low memory, great for scrapers and APIs, excellent K8s tooling |
| **Language — scripts/scrapers** | **Python** (optional) | Rich scraping ecosystem (Playwright, BeautifulSoup, Scrapy); use if Go HTTP is insufficient |
| **Frontend** | **Next.js (TypeScript)** | SSR, large ecosystem, easy Vercel deploy if needed |
| **Database** | **PostgreSQL 16** | ACID, excellent JSON support, pg_trgm for fuzzy text search |
| **Cache** | **Redis 7** | Session storage, API response cache, rate limiting via Redis Lua |
| **Message queue** | **RabbitMQ** | Simple to operate, good Go/Python clients, durable queues |
| **Container runtime** | **Docker** | Standard |
| **Orchestration** | **Kubernetes (EKS)** | Core learning goal; use k3d locally, EKS in prod |
| **Package manager (K8s)** | **Helm** | Templated manifests, environment promotion |
| **GitOps** | **ArgoCD** | Declarative deployments; free tier works well |
| **CI/CD** | **GitHub Actions** | Tight GitHub integration, free for open source |
| **IaC** | **Terraform** | Provision cloud resources (EKS cluster, RDS, etc.) |
| **Observability — metrics** | **Prometheus + Grafana** | Industry standard, native K8s integration |
| **Observability — logs** | **Grafana Loki** | Lightweight, integrates with existing Grafana |
| **Observability — traces** | **OpenTelemetry + Tempo** | Distributed tracing without vendor lock-in |
| **Email** | **Mailgun** | Already in design; good Australian deliverability |
| **Container registry** | **AWS ECR** | Native EKS integration; no cross-cloud auth friction |
| **DNS** | **AWS Route 53** | Managed DNS; integrates with ACM and ALB |
| **TLS** | **AWS ACM + ALB** | Free certs, auto-renewed, no cert-manager needed on EKS |
| **Ingress** | **AWS Load Balancer Controller + ALB** | Native AWS ingress for EKS; provisions ALBs automatically |
| **Secrets management** | **AWS Secrets Manager + External Secrets Operator** | Syncs AWS secrets into K8s Secrets; no secrets in Git |
| **Terraform state** | **S3 + DynamoDB lock table** | Standard AWS remote state backend |
| **Node autoscaling** | **Karpenter** | AWS-native, faster and more flexible than Cluster Autoscaler |

### Local Development Stack

```
docker-compose (or Tilt) for:
  - PostgreSQL
  - Redis
  - RabbitMQ
  - All backend services in hot-reload mode

k3d (k3s in Docker) for:
  - Testing K8s manifests locally before pushing
  - Simulating CronJobs, ingress, etc.
```

---

## 8. DevOps & Kubernetes Strategy

### 8.1 Repository Structure (Monorepo)

```
pricepilot-app/
├── services/
│   ├── scraper-woolworths/    # Go binary
│   ├── scraper-coles/         # Go binary
│   ├── price-service/         # Go binary
│   ├── user-service/          # Go binary
│   ├── notifier/              # Go binary
│   └── frontend/              # Next.js
├── charts/                    # Helm charts
│   ├── pricepilot/            # Umbrella chart
│   └── scrapers/
├── infra/                     # Terraform
│   ├── modules/
│   └── environments/
│       ├── dev/
│       └── prod/
├── .github/
│   └── workflows/             # CI/CD pipelines
├── docs/
│   └── diagrams/
└── PLANNING.md
```

### 8.2 Kubernetes Object Cheat Sheet (What You'll Learn)

| K8s Object | Where used in Price Pilot |
|---|---|
| `Deployment` | price-service, user-service, notifier, frontend |
| `CronJob` | Scrapers (daily), Notifier email trigger |
| `Service` | Internal ClusterIP per service |
| `Ingress` | External HTTP/S routing via nginx-ingress |
| `ConfigMap` | Non-secret config (store URLs, scrape schedule) |
| `Secret` | DB passwords, Mailgun API key, JWT secret |
| `PersistentVolumeClaim` | PostgreSQL, RabbitMQ data |
| `HorizontalPodAutoscaler` | Scale price-service under load |
| `NetworkPolicy` | Restrict which pods can talk to the database |
| `ServiceAccount` | Least-privilege identity per service |
| `Namespace` | Separate `dev`, `staging`, `prod` environments |

### 8.3 CI/CD Pipeline

```
On Pull Request:
  ├── Lint + unit tests (Go test, Jest)
  ├── Build Docker images
  ├── Security scan (Trivy for images, gosec for Go)
  └── Helm lint + dry-run

On merge to main:
  ├── Build + tag Docker images (SHA tag)
  ├── Push to container registry (GHCR or ECR)
  ├── Update Helm values with new image tag
  └── ArgoCD detects Git change → syncs to dev cluster

On release tag:
  └── ArgoCD promotes to prod (with manual approval gate)
```

### 8.4 Observability Stack

```
Every service:
  - Exposes /metrics endpoint (Prometheus format)
  - Structured JSON logging (zerolog for Go)
  - OpenTelemetry SDK for traces

Grafana dashboards:
  - Scraper success/failure rate and duration
  - Price freshness (age of newest price per store)
  - API request rate, latency, error rate (RED)
  - Email delivery rate
```

### 8.5 Environment Promotion Strategy

```
main branch → dev cluster (automatic via ArgoCD)
             ↓ (manual gate / PR to release branch)
           staging cluster
             ↓ (manual gate)
           prod cluster
```

---

## 9. Technical Risks & Mitigations

### Risk 1 — Scraper Fragility (HIGHEST RISK)

**Problem:** Woolworths and Coles do not expose a public API. The internal APIs
used by their apps can change without notice. Websites may deploy bot detection
(Cloudflare, CAPTCHA, IP blocking, User-Agent checks).

**Mitigations:**
- Abstract scraping logic behind a well-defined interface so changing
  implementation doesn't affect downstream services
- Write integration tests that validate the scraper output schema
- Alert on scraper failure within 1 h so you know immediately when it breaks
- Consider Playwright (headless Chrome) as a fallback for pages that block
  simple HTTP clients
- Maintain a mock/seed dataset for local development that doesn't rely on live
  sites

### Risk 2 — Legal & Terms of Service

**Problem:** Scraping supermarket websites may violate their ToS. In Australia,
the Computer Fraud and Abuse equivalent is the *Criminal Code Act 1995* and
state-level computer offence laws. Civil liability (breach of contract via ToS)
is more likely than criminal prosecution for a small project, but real.

**Mitigations:**
- Read the ToS of each supermarket — Woolworths and Coles generally prohibit
  automated access for commercial purposes
- Keep the project non-commercial while building
- Respect `robots.txt`
- Rate-limit scraper requests to mimic human browsing speed
- Explore whether either retailer has a formal data partnership program

### Risk 3 — Product Matching Complexity

**Problem:** "Woolworths Home Brand Milk 2L" and "Coles Brand Full Cream Milk
2L" are the same product but named differently. Matching them correctly is
non-trivial and critical to the core value proposition.

**Mitigations:**
- Start with barcode matching (EAN/UPC) where data is available
- Use PostgreSQL `pg_trgm` for fuzzy name matching as a starting point
- Build a simple admin review queue for unmatched products
- Keep unmatched products visible but clearly marked as store-specific
- Plan for an ML-based matching pipeline in a later phase

### Risk 4 — Operational Complexity of Kubernetes

**Problem:** Running a full K8s cluster (even managed EKS/GKE) has significant
operational overhead: upgrades, networking, persistent storage, debugging.

**Mitigations:**
- Start with **k3d** (k3s in Docker) locally — full K8s API without a cloud bill
- Use **EKS** with managed node groups in the cloud; start with a single `t3.medium`
  node and scale up only when needed
- Learn K8s incrementally: start with Deployments and Services, add CronJobs,
  then HPA, then NetworkPolicy
- Use Helm from day one to avoid raw manifest sprawl

### Risk 5 — Cost

**Problem:** A full production Kubernetes cluster + managed PostgreSQL + managed
Redis + bandwidth for scraping adds up quickly.

**Mitigations:**
- Development: run entirely on laptop with k3d + docker-compose
- Production: EKS with a single `t3.medium` managed node group to start
- Use **EC2 Spot instances** for scraper CronJob nodes via Karpenter (scrapers
  are retry-safe, so a spot interruption is harmless)
- PostgreSQL: **RDS `db.t3.micro`** to start; scale up only when needed
- **Note:** EKS control plane costs ~$0.10/hr (~$72/month) regardless of workload.
  Set a billing alert at $50 to catch surprises early
- Set billing alerts on your cloud provider from day one

### Risk 6 — Data Freshness vs. Scrape Load

**Problem:** Users expect current prices, but scraping too frequently risks
rate limiting and bans.

**Mitigations:**
- Daily scrapes are sufficient for grocery prices (prices rarely change
  intraday)
- Randomise scrape timing (not exactly midnight for every store)
- Cache aggressively in Redis; surface "last updated" timestamps in the UI
- For specials, run an additional lightweight scrape of just the specials page

---

## 10. Phased Roadmap

### Phase 1 — Foundation (Local, No K8s yet)
**Goal:** Working end-to-end scrape → store → query flow on localhost.

- [ ] Set up monorepo structure
- [ ] Build Woolworths scraper (Go) targeting internal API
- [ ] Define PostgreSQL schema and run migrations (golang-migrate)
- [ ] Build Price Service REST API (search, price history)
- [ ] docker-compose for all local dependencies
- [ ] Write integration tests with mock scraper output

### Phase 2 — User Features
**Goal:** Real users can sign up and use the app.

- [ ] Build User Service (JWT auth, shopping lists)
- [ ] Build Notifier Service (daily Mailgun email)
- [ ] Build Next.js frontend (search, list management)
- [ ] Add Coles scraper
- [ ] Basic product matching by barcode

### Phase 3 — Kubernetes (Local)
**Goal:** Everything running in k3d on your laptop.

- [ ] Dockerise all services
- [ ] Write Helm charts for each service
- [ ] Deploy to k3d: Deployments, Services, ConfigMaps, Secrets
- [ ] Convert scrapers to CronJobs
- [ ] Set up ingress-nginx locally
- [ ] Deploy Prometheus + Grafana (kube-prometheus-stack Helm chart)
- [ ] Deploy ArgoCD and point at the repo

### Phase 4 — Cloud & CI/CD
**Goal:** Deployed to a real cloud cluster with automated pipelines.

- [ ] Terraform: provision EKS cluster, RDS (PostgreSQL), ElastiCache (Redis), ECR repos
- [ ] GitHub Actions: build, test, scan, push images
- [ ] ArgoCD: GitOps promotion (dev → staging → prod)
- [ ] cert-manager + Let's Encrypt for TLS
- [ ] Set up Loki + Tempo (or use cloud equivalents)

### Phase 5 — Hardening & Polish
**Goal:** Production-grade reliability.

- [ ] NetworkPolicy (restrict DB access to only relevant services)
- [ ] Pod Disruption Budgets
- [ ] HorizontalPodAutoscaler for Price Service
- [ ] Sealed Secrets or Vault for secret management
- [ ] Scraper failure alerts (PagerDuty or simple email alert)
- [ ] Admin dashboard
- [ ] Price history charts in frontend
- [ ] ALDI scraper (HTML-only, no API available)

---

## 11. Open Questions

These need decisions before or during Phase 1:

1. ~~**Cloud provider preference?**~~ **Decided: AWS.** EKS for Kubernetes,
   RDS for PostgreSQL, ElastiCache for Redis, ECR for container images,
   Route 53 + ACM for DNS/TLS, Secrets Manager for secrets.

2. **Monorepo tool?** Plain Git is fine to start. If build times become
   painful, consider Turborepo (for JS) or Bazel.

3. **GraphQL vs REST?** REST is simpler. GraphQL is worth considering for the
   frontend if the query shapes are complex (e.g., "all items in my list with
   prices at all stores in one request").

4. **Authentication provider?** Roll your own JWT (good for learning) or
   delegate to a managed IdP like Auth0/Clerk (faster to ship, less to secure).

5. **Should scrapers run inside the cluster or as external lambda/serverless
   functions?** Inside the cluster as CronJobs is simpler for a K8s learning
   project.

6. **Data retention policy for price history?** Keeping all historical prices
   is valuable for trend charts but grows the database unboundedly. Partition
   the `prices` table by month and archive old partitions to object storage.
