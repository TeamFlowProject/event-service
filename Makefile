.PHONY: run
run:
	uv python -m src.main run

.PHONY: test
test:
	uv run pytest --cov=src
