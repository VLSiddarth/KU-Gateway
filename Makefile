.PHONY: help install run test lint docker-build docker-up clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install all dependencies
	pip install -e ".[dev]"

run:  ## Run the gateway locally
	uvicorn ku_gateway.main:app --host 0.0.0.0 --port 8000 --reload

test:  ## Run the test suite
	pytest -v

lint:  ## Lint the code
	ruff check src/ tests/

docker-build:  ## Build Docker image
	docker build -t ku-gateway:latest .

docker-up:  ## Start with docker-compose (gateway + mocks)
	docker-compose up --build

clean:  ## Clean caches and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache dist build *.egg-info