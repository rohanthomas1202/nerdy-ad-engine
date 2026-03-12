.PHONY: install test lint run demo clean

install:
	pip install -r requirements.txt

test:
	pytest -v

lint:
	ruff check src/ tests/

run:
	python -m src.main

demo:
	python -m src.main --demo

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	rm -rf .pytest_cache .ruff_cache output/*.json output/*.png
