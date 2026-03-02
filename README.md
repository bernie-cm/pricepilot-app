# Price Pilot

Aggregates grocery prices from Australian supermarkets (Woolworths, Coles) so
users can compare prices, build shopping lists, and receive daily digest emails
showing where to get the best deals.

Built as a production-grade, Kubernetes-native application on AWS.

## Architecture

See [PLANNING.md](./PLANNING.md) for the full architecture, tech stack, and
phased roadmap.

See [docs/adr/](./docs/adr/) for Architectural Decision Records.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend services | Python 3.12, FastAPI |
| Frontend | Next.js (TypeScript) |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Message queue | RabbitMQ |
| Orchestration | Kubernetes (EKS in prod, k3d locally) |
| IaC | Terraform |
| CI/CD | GitHub Actions + ArgoCD |

## Local Development

### Prerequisites

```
docker       https://docs.docker.com/get-docker/
k3d          https://k3d.io
kubectl      https://kubernetes.io/docs/tasks/tools/
helm         https://helm.sh/docs/intro/install/
python 3.12  https://www.python.org/downloads/
uv           https://docs.astral.sh/uv/getting-started/installation/
lefthook     https://lefthook.dev/installation/
```

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/bernie-cm/pricepilot-app.git
cd pricepilot-app

# 2. Install pre-commit hooks
make setup

# 3. Copy environment variables and fill in values
cp .env.example .env

# 4. Start local infrastructure (PostgreSQL, Redis, RabbitMQ)
make dev
```

PostgreSQL is available at `localhost:5432`.
Redis at `localhost:6379`.
RabbitMQ at `localhost:5672` (management UI at `http://localhost:15672`).

### Useful commands

```bash
make help    # list all available commands
make dev     # start local services
make down    # stop local services
make logs    # tail service logs
make lint    # run all linters
make test    # run all tests
```

## Contributing

See [WORKFLOW.md](./WORKFLOW.md) for the branching strategy, PR conventions,
and deployment guardrails.

All changes go through a Pull Request. CI must pass before merging.
No direct pushes to `main`.
