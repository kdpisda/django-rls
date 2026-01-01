.PHONY: help
help: ## Show this help message
	@echo 'Django RLS Development Commands'
	@echo '==============================='
	@echo ''
	@echo 'Usage: make [command]'
	@echo ''
	@echo 'Docker Commands:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E 'docker-|db-' | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'
	@echo ''
	@echo 'Testing Commands:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E 'test' | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'
	@echo ''
	@echo 'Development Commands:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -vE 'docker-|db-|test' | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

# Docker commands
.PHONY: docker-up
docker-up: ## Start PostgreSQL with docker-compose
	docker-compose up -d
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 3
	@docker-compose exec -T postgres pg_isready -U postgres || (echo "PostgreSQL not ready" && exit 1)
	@echo "PostgreSQL is ready!"

.PHONY: docker-down
docker-down: ## Stop PostgreSQL
	docker-compose down

.PHONY: docker-reset
docker-reset: ## Reset PostgreSQL (delete all data)
	docker-compose down -v
	docker-compose up -d
	@echo "PostgreSQL has been reset"

.PHONY: docker-logs
docker-logs: ## Show PostgreSQL logs
	docker-compose logs -f postgres

.PHONY: docker-test-up
docker-test-up: ## Start test PostgreSQL (lightweight, port 5433)
	docker-compose up -d test-postgres
	@echo "Waiting for test PostgreSQL to be ready..."
	@sleep 2
	@docker-compose exec -T test-postgres pg_isready -U postgres || (echo "Test PostgreSQL not ready" && exit 1)
	@echo "Test PostgreSQL is ready on port 5433!"

.PHONY: docker-test-down
docker-test-down: ## Stop test PostgreSQL
	docker-compose stop test-postgres

# Database commands
.PHONY: db-shell
db-shell: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U postgres -d test_django_rls

.PHONY: db-create
db-create: ## Create test database
	docker-compose exec postgres createdb -U postgres test_django_rls || echo "Database already exists"

.PHONY: db-drop
db-drop: ## Drop test database
	docker-compose exec postgres dropdb -U postgres test_django_rls || echo "Database doesn't exist"

.PHONY: db-reset
db-reset: db-drop db-create ## Reset test database

# Development setup
.PHONY: install
install: ## Install dependencies with poetry
	poetry install

.PHONY: install-dev
install-dev: install ## Install dev dependencies
	poetry install --with dev,docs
	poetry run pre-commit install

# Testing commands
.PHONY: test
test: ## Run all tests
	poetry run pytest

.PHONY: test-cov
test-cov: ## Run tests with coverage
	poetry run pytest --cov=django_rls --cov-report=term-missing --cov-report=html

.PHONY: test-security
test-security: ## Run security tests only
	poetry run pytest tests/test_security.py -v

.PHONY: test-fast
test-fast: ## Run tests without coverage (faster)
	poetry run pytest -n auto

.PHONY: test-failed
test-failed: ## Re-run failed tests
	poetry run pytest --lf

.PHONY: test-docker
test-docker: docker-test-up ## Run tests with test PostgreSQL container
	DATABASE_URL="postgres://postgres:postgres@localhost:5433/test_django_rls" poetry run pytest
	@$(MAKE) docker-test-down

.PHONY: test-watch
test-watch: ## Run tests in watch mode
	poetry run ptw -- -vx

# Code quality
.PHONY: lint
lint: ## Run all linters
	poetry run black --check .
	poetry run isort --check-only .
	poetry run flake8 .

.PHONY: format
format: ## Format code with black and isort
	poetry run black .
	poetry run isort .

.PHONY: type-check
type-check: ## Run type checking with mypy
	poetry run mypy django_rls

.PHONY: secure
secure: ## Run security checks
	poetry run bandit -r django_rls/
	poetry run pip-audit

# Coverage
.PHONY: coverage-html
coverage-html: ## Open HTML coverage report
	@if [ -d "htmlcov" ]; then \
		python -m webbrowser htmlcov/index.html; \
	else \
		echo "No coverage report found. Run 'make test-cov' first."; \
	fi

# Clean
.PHONY: clean
clean: ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/
	rm -rf dist/ build/ *.egg-info

# CI simulation
.PHONY: ci-local
ci-local: docker-up clean ## Run CI pipeline locally
	@echo "Running CI pipeline locally..."
	@$(MAKE) lint
	@$(MAKE) type-check
	@$(MAKE) test-cov
	@$(MAKE) test-security
	@echo "CI pipeline completed successfully!"

# Development workflow
.PHONY: dev
dev: docker-up ## Start development environment
	@echo "Development environment is ready!"
	@echo "PostgreSQL is running on localhost:5432"
	@echo "Run 'make test' to run tests"

.PHONY: dev-reset
dev-reset: docker-reset clean install ## Reset entire development environment
	@echo "Development environment has been reset!"