DB_DSN ?= postgresql://user:password@localhost:5432/event_db
MIGRATIONS_DIR = migrations

.PHONY: run
run:
	python -m src.main

.PHONY: test
test:
	uv run pytest --cov=src

.PHONY: migrate-up
migrate-up:
	migrate -path $(MIGRATIONS_DIR) -database "$(DB_DSN)" up

.PHONY: migrate-down
migrate-down:
	migrate -path $(MIGRATIONS_DIR) -database "$(DB_DSN)" down 1

.PHONY: migrate-drop
migrate-drop:
	migrate -path $(MIGRATIONS_DIR) -database "$(DB_DSN)" drop -f
