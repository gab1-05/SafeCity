# ─── SafeCity Makefile ────────────────────────────────────────
SHELL := /bin/bash
COMPOSE := docker compose

.PHONY: help install dev test test-frontend test-e2e lint format migrate seed superuser \
        docker-build docker-up docker-down docker-logs k8s-deploy terraform-plan terraform-apply \
        terraform-destroy coverage openapi

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Install backend + frontend dev dependencies
	cd backend && python -m venv .venv && .venv/Scripts/python -m pip install -r requirements/dev.txt || .venv/bin/python -m pip install -r requirements/dev.txt
	cd frontend && npm ci

dev: ## Run backend + frontend without Docker (2 shells)
	@echo "Shell 1: cd backend && .venv/Scripts/python manage.py runserver"
	@echo "Shell 2: cd frontend && npm run dev"

test: ## Run backend test suite
	cd backend && pytest

test-frontend: ## Run frontend unit tests
	cd frontend && npm run test -- --run

test-e2e: ## Run Playwright E2E suite against compose stack
	cd frontend && npx playwright test

lint: ## Lint backend and frontend
	cd backend && ruff check .
	cd frontend && npm run lint

format: ## Format backend and frontend
	cd backend && ruff check --fix . && ruff format .
	cd frontend && npm run format

migrate: ## Apply database migrations (Docker)
	$(COMPOSE) exec backend python manage.py migrate

seed: ## Load demo data (Docker)
	$(COMPOSE) exec backend python manage.py seed_demo_data

superuser: ## Create superuser (Docker)
	$(COMPOSE) exec backend python manage.py createsuperuser

docker-build: ## Build all Docker images
	$(COMPOSE) build

docker-up: ## Start the development stack
	$(COMPOSE) up -d --build
	@echo "Backend http://localhost:$${BACKEND_PORT:-18081}/api/v1/ · Swagger /api/schema/swagger/ · Frontend http://localhost:$${FRONTEND_PORT:-5174}"

docker-down: ## Stop the stack
	$(COMPOSE) down

docker-logs: ## Tail backend logs
	$(COMPOSE) logs -f backend

coverage: ## Backend coverage report
	cd backend && pytest --cov=apps --cov=config --cov-report=term-missing

openapi: ## Regenerate OpenAPI schema file
	cd backend && python manage.py spectacular --file ../docs/api-schema.yaml

k8s-deploy: ## Helm-deploy to the currently configured cluster (dev by default)
	helm upgrade --install safecity infrastructure/helm/safecity \
		-f infrastructure/helm/safecity/values-dev.yaml -n safecity-dev --create-namespace

terraform-plan: ## Terraform plan for dev (review output!)
	cd infrastructure/terraform/environments/dev && terraform init && terraform plan

terraform-apply: ## Terraform apply for dev — WILL CREATE AWS RESOURCES. Review plan first!
	@echo "⚠️  This creates real AWS resources and may incur charges."
	@echo "Run manually after reviewing: cd infrastructure/terraform/environments/dev && terraform apply"
	@exit 1

terraform-destroy: ## Terraform destroy for dev — DESTRUCTIVE. Never run blindly.
	@echo "⚠️  DESTRUCTIVE. Run manually: cd infrastructure/terraform/environments/dev && terraform destroy"
	@exit 1
