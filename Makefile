.PHONY: help setup start stop clean test lint

help: ## Show this help message
	@echo 'Usage:'
	@echo '  make <target>'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Setup the project (create directories, copy env file)
	@echo "Setting up project..."
	cp -n .env.example .env 2>/dev/null || true
	chmod +x scripts/*.sh
	./scripts/setup_directories.sh
	pip install -r requirements.txt
	pre-commit install

start: ## Start all services
	docker compose -f docker-compose.all.yml up -d

stop: ## Stop all services
	docker compose -f docker-compose.all.yml down

clean: ## Clean up containers, volumes, and temp files
	docker compose -f docker-compose.all.yml down -v
	rm -rf logs/* include/temp_data/* data/*

test: ## Run tests
	pytest

lint: ## Run linting
	black .
	flake8 .

logs: ## View logs
	docker compose -f docker-compose.all.yml logs -f

ps: ## Check container status
	docker compose -f docker-compose.all.yml ps

init-airflow: ## Initialize Airflow
	docker compose -f docker-compose.all.yml up airflow-init
