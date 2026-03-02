.PHONY: help setup dev down logs lint test

# Default target: print available commands
help: ## Show available make commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Install pre-commit hooks (run once after cloning)
	lefthook install
	@echo "Pre-commit hooks installed."

dev: ## Start local services (PostgreSQL, Redis, RabbitMQ)
	docker compose up -d
	@echo "Services running. PostgreSQL=5432  Redis=6379  RabbitMQ=5672 (UI=15672)"

down: ## Stop local services
	docker compose down

logs: ## Tail logs from all local services
	docker compose logs -f

lint: ## Run linters against all services
	ruff format --check services/
	ruff check services/
	mypy services/

test: ## Run all tests
	pytest services/ -v
