# Web Scraper Makefile
# Simple commands for easy project management

.PHONY: help install test scrape docker-build docker-run docker-stop clean

# Default target
help:
	@echo "Web Scraper - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  make install    - Install dependencies"
	@echo "  make test       - Run all tests"
	@echo "  make scrape     - Quick test scrape (httpbin.org)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-run   - Run with Docker Compose"
	@echo "  make docker-stop  - Stop Docker containers"
	@echo ""
	@echo "Utility:"
	@echo "  make clean      - Clean up generated files"
	@echo "  make help       - Show this help"

# Install dependencies
install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt

# Run tests
test:
	@echo "Running tests..."
	@echo "Testing scraper import..."
	PYTHONPATH=. python -c "from src.scraper.universal_scraper import UniversalScraper; print('✓ Scraper import successful')"
	@echo "Testing CLI help..."
	PYTHONPATH=. python src/cli.py --help > /dev/null && echo "✓ CLI help successful"
	@echo "Testing basic scrape..."
	PYTHONPATH=. python src/cli.py https://httpbin.org --max-pages 2 --max-workers 3
	@echo ""
	@echo "Running multithreading tests..."
	PYTHONPATH=. python test_multithreading.py
	@echo ""
	@echo "✓ All tests completed successfully!"

# Quick test scrape
scrape:
	@echo "Running quick test scrape..."
	PYTHONPATH=. python src/cli.py https://httpbin.org --max-pages 3 --max-workers 5

# Docker commands
docker-build:
	@echo "Building Docker image..."
	docker-compose build

docker-run:
	@echo "Starting Docker containers..."
	docker-compose up -d

docker-stop:
	@echo "Stopping Docker containers..."
	docker-compose down

# Clean up generated files
clean:
	@echo "Cleaning up generated files..."
	rm -rf data/raw/scraped_*
	rm -rf data/processed/*
	rm -rf data/vectorstore/*
	@echo "✓ Cleanup completed"

# Development server
dev-server:
	@echo "Starting development server..."
	PYTHONPATH=. python -m src.api.main

# Interactive scraping
interactive:
	@echo "Starting interactive scraping..."
	PYTHONPATH=. python src/cli.py https://httpbin.org --interactive 