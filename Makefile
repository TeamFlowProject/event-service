DB_DSN ?= postgresql://user:password@localhost:5432/event_db
MIGRATIONS_DIR = migrations
COMPOSE_FILE = compose.yaml
COMPOSE_ENV_FILES = \
	--env-file .env_krakend \
	--env-file .env_event_service \
	--env-file .env_postgres \
	--env-file .env_redpanda \
	--env-file .env_redpanda_console \
	--env-file .env_jaeger \
	--env-file .env_prometheus \
	--env-file .env_grafana \
	--env-file .env_loki \
	--env-file .env_promtail

.PHONY: run
run:
	python -m src.main run

.PHONY: unit-test
unit-test:
	uv run pytest --cov=src -m unit

.PHONY: integration-test
integration-test:
	uv run pytest --cov=src -m integration

.PHONY: test
test: unit-test integration-test

.PHONY: migrate-up
migrate-up:
	python -m src.main migrate

.PHONY: migrate-down
migrate-down:
	python -m src.main migrate-down

.PHONY: migrate-drop
migrate-drop:
	python -m src.main migrate-drop

.PHONY: install-tools
install-tools:
	uv tool install pyright
	uv tool install ruff

.PHONY: lint
lint:
	uv tool run pyright .
	uv tool run ruff check .
	uv tool run ruff format --check .

.PHONY: lint-fix
lint-fix:
	uv tool run ruff check --fix .
	uv tool run ruff format .

.PHONY: compose-config compose-up compose-down init-env
compose-config:
	docker compose $(COMPOSE_ENV_FILES) -f $(COMPOSE_FILE) config

compose-up:
	docker compose $(COMPOSE_ENV_FILES) -f $(COMPOSE_FILE) up --build

compose-down:
	docker compose $(COMPOSE_ENV_FILES) -f $(COMPOSE_FILE) down

init-env:
	@test -f .env_event_service || cp .env_event_service.example .env_event_service
	@test -f .env_krakend || printf '%s\n' 'KRAKEND_PORT=8000' > .env_krakend
	@test -f .env_postgres || printf '%s\n' \
		'POSTGRES_PORT=5432' 'POSTGRES_DB=event_db' 'POSTGRES_USER=user' 'POSTGRES_PASSWORD=password' > .env_postgres
	@test -f .env_redpanda || printf '%s\n' \
		'REDPANDA_EXTERNAL_PORT=19092' \
		'REDPANDA_KAFKA_ADDR=internal://0.0.0.0:9092,external://0.0.0.0:19092' \
		'REDPANDA_ADVERTISE_KAFKA_ADDR=internal://redpanda:9092,external://localhost:19092' \
		'REDPANDA_SMP=1' 'REDPANDA_MEMORY=1024M' 'REDPANDA_LOG_LEVEL=warn' > .env_redpanda
	@test -f .env_redpanda_console || printf '%s\n' \
		'REDPANDA_CONSOLE_PORT=8080' 'KAFKA_BROKERS=redpanda:9092' > .env_redpanda_console
	@test -f .env_jaeger || printf '%s\n' \
		'JAEGER_UI_PORT=16686' 'JAEGER_OTLP_GRPC_PORT=4317' 'JAEGER_OTLP_HTTP_PORT=4318' \
		'COLLECTOR_OTLP_ENABLED=true' > .env_jaeger
	@test -f .env_prometheus || printf '%s\n' 'PROMETHEUS_PORT=9090' > .env_prometheus
	@test -f .env_grafana || printf '%s\n' \
		'GRAFANA_PORT=3000' 'GF_AUTH_ANONYMOUS_ENABLED=true' \
		'GF_AUTH_ANONYMOUS_ORG_ROLE=Admin' 'GF_LOG_LEVEL=warn' > .env_grafana
	@test -f .env_loki || printf '%s\n' 'LOKI_PORT=3100' > .env_loki
	@test -f .env_promtail || printf '%s\n' \
		'PROMTAIL_HTTP_LISTEN_PORT=9080' \
		'LOKI_PUSH_URL=http://loki:3100/loki/api/v1/push' > .env_promtail
	@echo "Env files are ready."
