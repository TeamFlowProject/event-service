DB_DSN ?= postgresql://user:password@localhost:5432/event_db
MIGRATIONS_DIR = migrations

.PHONY: run
run:
	python -m src.main run

.PHONY: unit-test
unit-test:
	uv run pytest --cov=src -m unit

.PHONY: integration-test
integration-test:
	uv run pytest --cov=src

.PHONY: migrate-up
migrate-up:
	python -m src.main migrate

.PHONY: migrate-down
migrate-down:
	python -m src.main migrate-down

.PHONY: migrate-drop
migrate-drop:
	python -m src.main migrate-drop
