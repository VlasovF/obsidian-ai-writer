.PHONY: help up down logs ps clean

help:
	@echo "Awailable commands:"
	@echo "  make up         - Up containes"
	@echo "  make down       - Down contaienrs"
	@echo "  make logs       - show logs"
	@echo "  make ps         - show status"
	@echo "  make clean      - stop and clean all"
	@echo "  make health     - healthcheck"

up:
	docker compose up -d
	@echo "Containers up"
	@echo "Check status: make ps"

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

clean:
	docker compose down -v
	@echo "Containers and volumes deleted"

health:
	docker compose exec app python /app/scripts/healthcheck.py || true