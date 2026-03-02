# Price Pilot — Collaboration & Workflow Guide

> How we work together: roles, branching, CI/CD guardrails, and learning conventions.

---

## 1. The Collaboration Model

### Roles

| Who | Does what |
|---|---|
| **You** | Decide what to build next, review all code before it merges, approve deployments, ask questions |
| **Claude** | Propose implementations, write code and config, explain every decision, flag tradeoffs |

### The core rule: nothing merges or deploys without your eyes on it

Claude will never push directly to `main` and will never trigger a deployment.
Every piece of work ends with a Pull Request that you read, question, and merge
yourself. If you don't understand something in a PR, that's a signal to pause
and discuss — not to click Merge and move on.

### How a typical session works

```
1. You describe what you want to work on next
2. Claude explains the approach and WHY before writing anything
   (if the approach is non-obvious, we agree on it first)
3. Claude creates a feature branch and implements the change
4. Claude opens a Pull Request with:
   - A plain-English explanation of what changed and why
   - Learning notes on any new concepts introduced
   - A testing checklist for you to run before merging
5. You read the PR, ask questions, request changes if needed
6. You merge when satisfied
7. CI runs automatically on merge; you watch it pass
8. For deployments: you trigger them explicitly (never automatic to prod)
```

---

## 2. Git Branching Strategy

We follow **GitHub Flow** — simple, linear, and easy to learn.

```
main (protected)
 │
 ├── feat/woolworths-scraper
 ├── feat/user-auth
 ├── feat/price-api
 ├── fix/scraper-timeout
 ├── chore/update-helm-chart
 └── docs/add-adr-001
```

### Branch naming conventions

| Prefix | When to use | Example |
|---|---|---|
| `feat/` | New functionality | `feat/shopping-list-api` |
| `fix/` | Bug fixes | `fix/coles-scraper-parse-error` |
| `chore/` | Infrastructure, config, dependencies | `chore/add-github-actions` |
| `docs/` | Documentation only | `docs/c4-container-diagram` |
| `test/` | Adding or fixing tests | `test/price-service-unit-tests` |

### `main` branch protection rules (set these in GitHub)

- [ ] Require pull request before merging (no direct pushes)
- [ ] Require at least 1 approving review (you approve your own PRs after reading)
- [ ] Require status checks to pass before merging (CI must be green)
- [ ] Do not allow bypassing the above rules — even for admins

> **Why?** These rules make it physically impossible to accidentally push broken
> code to main. You'll see this pattern on every professional engineering team.

---

## 3. Pull Request Convention

Every PR follows this structure. Claude will generate this for every change.

### PR title format
```
<type>(<scope>): <short description>

Examples:
feat(scraper): add Woolworths product scraper with RabbitMQ publishing
fix(user-service): correct JWT expiry on refresh token
chore(ci): add Docker build and push workflow
```

### PR description template

```markdown
## What changed
<!-- Plain English. What does this PR do? -->

## Why
<!-- The motivation. What problem does this solve? -->

## 📚 Learning note
<!-- New concepts introduced in this PR. Links to docs. -->
<!-- E.g.: "This PR introduces Kubernetes CronJobs. A CronJob is..." -->

## How to test
<!-- Step-by-step checklist for you to verify this works -->
- [ ] Step 1
- [ ] Step 2

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated if needed
- [ ] No secrets or credentials in code
```

---

## 4. CI/CD Pipeline

### Philosophy: CI is a safety net, not a bureaucracy

Every automated check exists for a specific reason. When a check is added,
there will always be an explanation of what it catches and why it matters.

### Pipeline stages (GitHub Actions)

```
On every Pull Request:
┌─────────────────────────────────────────────────────┐
│ PR Checks (must all pass before you can merge)      │
│                                                     │
│  lint          → code style, formatting             │
│  test          → unit + integration tests           │
│  build         → Docker image builds successfully   │
│  security-scan → Trivy (container vulns)            │
│                  gosec (Go security issues)         │
│  helm-lint     → Kubernetes manifests are valid     │
└─────────────────────────────────────────────────────┘

On merge to main:
┌─────────────────────────────────────────────────────┐
│ Release pipeline                                    │
│                                                     │
│  build + tag   → Docker image tagged with Git SHA   │
│  push          → Image pushed to container registry │
│  update-chart  → Helm values updated with new tag   │
└─────────────────────────────────────────────────────┘
```

### Why each stage exists

| Stage | What it catches |
|---|---|
| **lint** | Style inconsistencies; keeps the codebase readable as it grows |
| **test** | Regressions — code that used to work and no longer does |
| **build** | "Works on my machine" problems — if it doesn't build in CI, it won't deploy |
| **security-scan** | Known CVEs in base images and dependencies; hardcoded secrets |
| **helm-lint** | Malformed Kubernetes manifests that would cause a silent deploy failure |

---

## 5. Pre-commit Hooks

### Why this is a separate layer from CI

CI (GitHub Actions) is the **authoritative, team-wide gate** — it runs in the
cloud and cannot be skipped without bypassing branch protection. Pre-commit
hooks are a **local, fast feedback loop** — they run on your machine the moment
you type `git commit`, before the code ever leaves your laptop.

```
You type: git commit
          │
          ▼
  ┌─────────────────────┐     fails?    fix and re-commit
  │  Pre-commit hooks   │──────────────▶ (seconds, local)
  │  (local, fast)      │
  └────────┬────────────┘
           │ passes
           ▼
     Commit created
           │
           ▼
     git push → PR opened
           │
           ▼
  ┌─────────────────────┐     fails?    PR blocked, fix in a new commit
  │  CI (GitHub Actions)│──────────────▶ (minutes, remote)
  │  authoritative gate │
  └─────────────────────┘
           │ passes
           ▼
     You can merge
```

The two layers are complementary. Hooks give you instant feedback ("your
formatting is wrong") without waiting 3 minutes for CI. CI gives you a
guarantee that no one on the team — including you on a bad day — can merge
broken code even if they skip the hooks.

> **Important:** Hooks can be bypassed with `git commit --no-verify`. This is
> intentional — sometimes you need to commit a work-in-progress. It's not a
> security hole because CI will still block the PR. Bypassing hooks is allowed;
> bypassing CI is not.

### Tool: Lefthook

We use **Lefthook** — a single Go binary, fast (runs hooks in parallel),
monorepo-friendly, and configured via a single `lefthook.yml` in the repo root.

```bash
# Install once (macOS/Linux)
brew install lefthook        # or: go install github.com/evilmartians/lefthook@latest

# Wire it to your local Git repo (run once after cloning)
lefthook install
```

The `lefthook install` command writes the actual Git hook scripts into
`.git/hooks/`. From then on, every `git commit` triggers Lefthook automatically.
The config file (`lefthook.yml`) lives in the repo so everyone gets the same
hooks.

### Hook configuration (`lefthook.yml`)

```yaml
# Runs before every commit is created.
pre-commit:
  parallel: true   # run all hooks at the same time for speed
  commands:

    # --- Secret detection (highest priority) ---
    gitleaks:
      run: gitleaks protect --staged --redact --no-git
      # Scans staged files for API keys, tokens, passwords.
      # Catches the #1 most damaging accidental mistake in git history.

    # --- Go ---
    go-fmt:
      glob: "services/**/*.go"
      run: gofmt -l {staged_files} | grep . && exit 1 || exit 0
      # Enforces standard Go formatting. gofmt is non-negotiable in Go —
      # there is one correct style and this enforces it.

    go-vet:
      glob: "services/**/*.go"
      run: cd {0} && go vet ./...
      # Catches suspicious Go constructs the compiler accepts but are
      # likely bugs (e.g., unreachable code, misused sync primitives).

    golangci-lint:
      glob: "services/**/*.go"
      run: golangci-lint run --fix {staged_files}
      # Runs ~50 linters in one pass. Catches everything from inefficient
      # code to security issues. --fix auto-corrects where possible.

    # --- TypeScript / Next.js ---
    prettier:
      glob: "services/frontend/**/*.{ts,tsx,json,css}"
      run: prettier --write {staged_files}
      # Auto-formats frontend code. Like gofmt, removes all style debates.

    eslint:
      glob: "services/frontend/**/*.{ts,tsx}"
      run: eslint --fix {staged_files}
      # Catches TypeScript/React bugs and enforces best practices.

    # --- Infrastructure ---
    terraform-fmt:
      glob: "infra/**/*.tf"
      run: terraform fmt -check {staged_files}
      # Enforces standard Terraform formatting.

    helm-lint:
      glob: "charts/**"
      run: helm lint charts/pricepilot
      # Validates Helm chart structure and template syntax.

    hadolint:
      glob: "**/Dockerfile*"
      run: hadolint {staged_files}
      # Lints Dockerfiles for best practices (e.g., pinned base image
      # versions, no root user, layer ordering).

    yamllint:
      glob: "**/*.{yml,yaml}"
      run: yamllint {staged_files}
      # Catches YAML syntax errors early — a malformed K8s manifest
      # silently fails at apply time without this.

# Runs before every push (heavier checks, worth the extra seconds).
pre-push:
  commands:
    go-test:
      glob: "services/**/*.go"
      run: cd {0} && go test ./...
      # Run tests before pushing so you don't open a PR you know is broken.
```

### Hook summary: what each one protects

| Hook | Layer | What it prevents |
|---|---|---|
| `gitleaks` | Security | Leaked API keys, passwords, tokens in Git history |
| `go-fmt` | Quality | Inconsistent Go formatting across the codebase |
| `go-vet` | Quality | Likely Go bugs the compiler allows |
| `golangci-lint` | Quality | A wide class of Go bugs, security issues, inefficiencies |
| `prettier` | Quality | Inconsistent frontend formatting |
| `eslint` | Quality | TypeScript/React bugs and anti-patterns |
| `terraform-fmt` | Quality | Inconsistent Terraform formatting |
| `helm-lint` | Correctness | Broken Helm charts that would fail at deploy time |
| `hadolint` | Security/Quality | Insecure or inefficient Dockerfiles |
| `yamllint` | Correctness | Invalid YAML that silently breaks K8s manifests |
| `go-test` (pre-push) | Correctness | Pushing code you know has failing tests |

### Required tools for hooks (add to local setup)

```
lefthook       — hook runner
gitleaks       — secret scanning
golangci-lint  — Go linter suite
hadolint       — Dockerfile linter
yamllint       — YAML linter
prettier       — frontend formatter
eslint         — TypeScript linter
terraform      — needed for terraform fmt (already needed for IaC)
helm           — needed for helm lint (already needed for K8s)
```

---

## 6. Deployment Guardrails

### Environments

```
dev (automatic)  →  staging (manual trigger)  →  prod (manual trigger + checklist)
```

| Environment | Who triggers | When | Purpose |
|---|---|---|---|
| **dev** | ArgoCD (automatic on merge to main) | Every merge | Smoke-test in a real cluster |
| **staging** | You (ArgoCD UI or `argocd app sync`) | Before releases | Full QA; share with others |
| **prod** | You (explicit ArgoCD sync with manual gate) | Deliberate releases | Live users |

### Production deployment checklist (enforced as a GitHub Environment)

Before prod can be targeted, GitHub requires you to manually approve a
deployment in the GitHub UI. The approval gate will show:

```
□ Staging has been running this version for at least N hours
□ No open P1 bugs against this version
□ Scraper health checks are green
□ You have reviewed the diff since the last prod deploy
```

> **Why manual gates?** Fully automatic prod deploys are fine for mature teams
> with extensive test coverage. For a learning project where you want to
> understand every change going to production, a manual gate ensures you're
> never surprised by what's running live.

### ArgoCD sync policy

| Environment | Sync policy | What this means |
|---|---|---|
| dev | `automated` (selfHeal + prune) | ArgoCD watches Git and syncs immediately |
| staging | `automated` (no selfHeal) | Syncs when you push, but doesn't auto-revert manual changes |
| prod | `manual` | ArgoCD only syncs when you explicitly press "Sync" |

---

## 7. Learning Conventions

### Architectural Decision Records (ADRs)

Every significant technical decision is recorded in `docs/adr/` using a
lightweight format. This builds a log of *why* the project is structured the
way it is — invaluable when you revisit decisions months later.

```
docs/
└── adr/
    ├── 001-use-rabbitmq-over-kafka.md
    ├── 002-go-as-primary-language.md
    └── 003-github-flow-branching.md
```

ADR format:
```markdown
# ADR-001: Use RabbitMQ over Kafka

## Status: Accepted

## Context
We need a message queue for scraper → processor communication.

## Decision
We chose RabbitMQ.

## Reasoning
Kafka is operationally heavier and designed for high-throughput event streaming.
Our scraper publishes a few thousand messages per day — RabbitMQ is sufficient
and far simpler to run in Kubernetes.

## Consequences
If we later need replay/event sourcing, we would need to migrate.
```

### Code comments

Comments in production code explain **why**, not **what**. The code already
shows what. Claude will add explanatory comments only where the reasoning
is non-obvious.

For learning, K8s manifests and CI config files will have inline annotations
like:

```yaml
# HPA: automatically add more pods when CPU exceeds 70%.
# This means the price-service can handle traffic spikes without manual scaling.
autoscaling:
  enabled: true
  targetCPUUtilizationPercentage: 70
```

### "Stop and learn" moments

When a PR introduces a concept you haven't seen before (e.g., PodDisruptionBudgets,
IRSA, Sealed Secrets), Claude will include a short explanation in the PR body
and optionally a link to the official docs. If you want to go deeper on any
topic, just say so — we can pause implementation and explore the concept.

---

## 8. What We Won't Compromise On

These are non-negotiable regardless of pace or scope:

1. **No secrets in Git** — ever. Passwords, API keys, tokens go in K8s Secrets
   or a secrets manager, referenced by name only in code.
2. **No bypassing CI** — if CI is broken, we fix the root cause. The only
   acceptable reason to merge with failing checks is a documented CI
   infrastructure outage, and that requires explicit discussion.
3. **No direct pushes to `main`** — all changes go through PRs.
4. **No production deploys without your explicit approval.**
5. **Every PR has tests** — if a feature can be tested, it will be tested.
6. **Pre-commit hooks stay installed** — `lefthook install` is part of the
   project setup. Hooks may be bypassed with `--no-verify` for genuine
   work-in-progress commits, but never to skip a check you know will fail
   on CI.

---

## 9. Tooling You'll Need Locally

Before we start Phase 1, make sure you have:

```
git          — version control (you already have this)
gh           — GitHub CLI (open PRs, view CI from terminal)
docker       — container builds and local dependencies
k3d          — local Kubernetes cluster (k3s in Docker)
kubectl      — talk to Kubernetes clusters
helm         — package Kubernetes applications
go 1.22+     — primary backend language
node 20+     — Next.js frontend
```

Pre-commit hook tools (required once hooks are wired up):
```
lefthook        — hook runner (install via brew or go install)
gitleaks        — secret scanning
golangci-lint   — Go linter suite
hadolint        — Dockerfile linter
yamllint        — YAML linter
prettier        — frontend formatter (installed via npm)
eslint          — TypeScript linter (installed via npm)
```

Optional but recommended:
```
k9s          — terminal UI for Kubernetes (makes cluster navigation fast)
stern        — tail logs from multiple pods at once
argocd CLI   — interact with ArgoCD from terminal
aws CLI      — interact with AWS services; configure with your IAM credentials
eksctl       — provision and manage EKS clusters from the terminal
```

---

## 10. First Steps

Decisions confirmed:
- GitHub repo: https://github.com/bernie-cm/pricepilot-app
- Cloud provider: AWS (EKS, RDS, ECR, Route 53, ACM, Secrets Manager)
- Branch protection rules: you'll configure these yourself in GitHub Settings

Next session — first implementation PR:
1. **Monorepo skeleton** — directory structure, `.gitignore`, `Makefile`,
   `docker-compose.yml` for local dependencies
2. **ADR-001** — document the architecture and AWS decisions
3. **First real feature:** Woolworths scraper (Phase 1)
