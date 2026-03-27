.PHONY: lint format typecheck test check

lint:
	ruff check src tests

format:
	ruff format src tests

typecheck:
	mypy src

test:
	pytest

check: lint typecheck test
