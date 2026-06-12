.PHONY: install test lint format run clean

install:
	pip install -r requirements.txt -r requirements-dev.txt

test:
	pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing

lint:
	flake8 .
	mypy .

format:
	black .

run:
	python -m api.server

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov

all: format lint test
