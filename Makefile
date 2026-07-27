.PHONY: help up down logs ps clean health test lint format pre-commit

help:
	@echo "Available commands:"
	@echo "  make up          - Start all containers"
	@echo "  make down        - Stop all containers"
	@echo "  make logs        - Show logs of all containers"
	@echo "  make ps          - Show container status"
	@echo "  make clean       - Stop and remove containers, volumes"
	@echo "  make health      - Check service health"
	@echo "  make test        - Run tests"
	@echo "  make lint        - Run ruff and mypy"
	@echo "  make format      - Run ruff formatter"
	@echo "  make pre-commit  - Install pre-commit hooks"

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

clean:
	docker compose down -v

health:
	docker compose exec api python /app/scripts/healthcheck.py || true

test:
	docker compose run --rm api pytest tests/ -v

lint:
	docker compose run --rm api ruff check src/
	docker compose run --rm api mypy src/

format:
	docker compose run --rm api ruff format src/

fix:
	docker compose run --rm api ruff check --fix src/
	docker compose run --rm api ruff format src/

pre-commit:
	uv sync --dev
	uv run pre-commit install
	uv run pre-commit run --all-files