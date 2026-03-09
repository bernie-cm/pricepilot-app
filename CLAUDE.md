# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Infrastructure (local dev dependencies: Postgres, Redis, RabbitMQ)
make dev          # docker compose up -d
make down         # docker compose down
make logs         # tail all service logs

# Hooks
make setup        # lefthook install (run once after cloning)

# Per-service (run from services/<name>/)
uv run pytest                        # run all tests
uv run pytest tests/test_foo.py::test_bar  # run a single test
uv run ruff format .                 # format Python code
uv run ruff check . --fix            # lint Python with auto-fix
uv run mypy .                        # static type check
uv run bandit -r . -ll               # security scan (medium+ severity)

# From repo root
make lint         # ruff format + ruff check + mypy across all services
make test         # pytest across all services
```

## Repository Structure

```
services/             # One directory per microservice
  price-service/      # FastAPI — only implemented service so far
  user-service/       # (scaffold only) auth/users
  scraper-woolworths/ # (scaffold only) CronJob scraper
  scraper-coles/      # (scaffold only) CronJob scraper
  notifier/           # (scaffold only) email via Mailgun
  frontend/           # (scaffold only) Next.js
infra/
  environments/dev/   # Terraform: dev EKS cluster
  environments/prod/  # Terraform: prod EKS cluster
  modules/            # Reusable Terraform modules
charts/pricepilot/    # Helm umbrella chart (scaffold only)
docs/adr/             # Architecture Decision Records
.github/workflows/    # GitHub Actions CI (ci.yml)
lefthook.yml          # Pre-commit/pre-push hook definitions
docker-compose.yml    # Local dev infrastructure only (no app services)
Makefile              # Convenience targets wrapping docker compose / uv
```

## Architecture

Price Pilot scrapes grocery prices from Australian supermarkets (Woolworths, Coles, ALDI) and lets users track prices and receive email alerts.

**Request path:** Browser → nginx-ingress → User Service (auth/JWT) or Price/Product Service (queries) → PostgreSQL + Redis (cache)

**Scrape path:** K8s CronJob (scraper) → RabbitMQ → Price Service (consumer) → PostgreSQL

**Notification path:** Price Service publishes events → RabbitMQ → Notifier → Mailgun

Key design choices:
- Scrapers are K8s CronJobs (ephemeral, not always-on services); they use Playwright to hit internal supermarket APIs
- RabbitMQ decouples scrapers from the Price Service; chosen over Kafka because daily scrape volume is low
- Each Python service manages its own `pyproject.toml` and virtual env via `uv`; no shared library across services (deliberate)
- Production target: AWS EKS + RDS PostgreSQL + ElastiCache Redis + ECR + ArgoCD (GitOps)

## Python Stack

All backend services use: Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, aio-pika, uv, Playwright (scrapers only). Line length: 120. Tests use pytest + httpx.

## CI Pipeline

Five jobs run on every PR to `main`:
1. **validate** — yamllint + helm-lint
2. **lint-python** — ruff format, ruff lint, mypy, bandit
3. **test** (depends on lint-python) — pytest
4. **lint-docker** — hadolint
5. **ci-pass** (gate, depends on all) — only job in branch protection rules

Jobs are skipped if no relevant files exist (e.g., lint-python skips if no `.py` files). The single gate job (`ci-pass`) is what's added to GitHub branch protection — never add individual jobs there.

## Pre-commit Hooks (Lefthook)

Hooks run in parallel on `pre-commit`: gitleaks (secrets), ruff-format, ruff-lint, mypy, bandit, prettier, eslint, terraform-fmt, helm-lint, hadolint, yamllint.

`pre-push` runs pytest.

Use `--no-verify` only for WIP commits that will be squashed before PR; CI cannot be bypassed.

## Collaboration Conventions

- **Claude writes:** infrastructure (Terraform, Helm, K8s manifests), CI/CD config, config files, IaC — always with explanatory comments for learning
- **User writes:** all application code (Python services, frontend)
- **Claude opens PRs** with learning notes; user reviews and merges — Claude never merges
- **User runs all git commands**; Claude provides exact commands when non-obvious
- **ADRs** go in `docs/adr/` for every significant architecture decision

## Branch & Commit Rules

- GitHub Flow: `feat/`, `fix/`, `chore/`, `docs/`, `test/` branches → PR → merge
- Never push directly to `main`; never commit `.env` or real secrets
- PR titles follow Conventional Commits: `feat(scope): description`

## Environment Setup

Copy `.env.example` to `.env` and fill in values. The docker-compose services read from `.env` at startup. Never commit `.env`.

---

## Progress Log

This section tracks implementation progress across sessions.

### Current Branch: `feat/price-service-skeleton`

**Goal:** Build the price-service with REST API and RabbitMQ consumer to store and query product/price data.

**Last Updated:** 2026-03-07

### Phase 1: Price Service — Task List

#### Completed
- [x] Set up monorepo structure with dev tooling (ADR-001)
- [x] Add GitHub Actions CI pipeline
- [x] Create `pyproject.toml` and install dependencies
- [x] Add PostgreSQL + Alembic infrastructure
- [x] Create `Product` model and Alembic migration
- [x] Create `Price` model and Alembic migration
- [x] Add FastAPI app entry point with `/health` endpoint
- [x] Add `GET /prices` router (lists all prices)
- [x] Add `GET /products` router (list/search products)

#### In Progress
- [ ] Add `GET /prices?product_id=X` filtering (prices for a specific product)

#### Up Next
- [ ] Add `GET /products/{id}` endpoint (single product with latest price)
- [ ] Build RabbitMQ consumer to process incoming scrape data
- [ ] Add Pydantic schemas for request/response validation
- [ ] Write integration tests for API endpoints
- [ ] Add Redis caching for frequently queried products

#### Future (after price-service skeleton)
- [ ] Woolworths scraper (K8s CronJob)
- [ ] Coles scraper
- [ ] User Service (auth, shopping lists)
- [ ] Notifier Service (daily email digest)

### CI/CD Progression

This project follows a staged approach to CI/CD, building up to a production-like GitOps workflow.

#### Stage 1: GitHub Actions CI (Current)
- [x] CI pipeline with 5 jobs: validate, lint-python, test, lint-docker, ci-pass
- [x] Branch protection requiring `ci-pass` before merge
- [x] Pre-commit hooks via Lefthook (local quality gates)
- [ ] Add Docker image build step (triggered on PR)
- [ ] Add container security scanning (Trivy)

#### Stage 2: Local Kubernetes (k3d)
- [ ] Dockerise price-service
- [ ] Write Helm chart for price-service
- [ ] Deploy to k3d cluster locally
- [ ] Set up nginx-ingress
- [ ] Deploy Prometheus + Grafana for observability

#### Stage 3: ArgoCD (GitOps)
- [ ] Deploy ArgoCD to k3d
- [ ] Configure ArgoCD Application pointing to Helm chart
- [ ] Implement image tag update workflow (CI builds → ArgoCD syncs)
- [ ] Add sync waves for dependency ordering

#### Stage 4: Cloud Deployment (AWS EKS)
- [ ] Terraform: EKS cluster, RDS, ElastiCache, ECR
- [ ] GitHub Actions: push images to ECR
- [ ] ArgoCD: multi-environment promotion (dev → staging → prod)
- [ ] cert-manager + Let's Encrypt for TLS

**DevOps concepts covered:** Each stage introduces new concepts that will be explained as we implement them — container orchestration, declarative config, GitOps principles, infrastructure as code, observability, and environment promotion strategies.

### Session Notes

**2026-03-07:** Reviewed codebase structure and git history. Identified next step as adding products router, following same pattern as prices router. User wants to be hands-on with coding and learn DevOps concepts along the way. Methodology: explain business problems solved by technical choices.
