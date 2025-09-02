# ScrapeJET Production Makefile
# Commands for managing the production-grade scraping system

.PHONY: help install test scrape docker-build docker-run docker-stop clean docker-dev start-workers start-api monitor

# Default target
help:
	@echo "ScrapeJET - Available Commands:"
	@echo ""
	@echo "🚀 Quick Start:"
	@echo "  make start         - Start complete production system"
	@echo "  make stop          - Stop all services"
	@echo "  make status        - Check system status"
	@echo "  make monitor       - Open monitoring dashboards"
	@echo ""
	@echo "🔧 Development:"
	@echo "  make install       - Install dependencies"
	@echo "  make test          - Run all tests"
	@echo "  make dev-api       - Start API in development mode"
	@echo "  make dev-worker    - Start single worker for development"
	@echo ""
	@echo "📦 Docker (Production):"
	@echo "  make docker-build  - Build Docker images"
	@echo "  make docker-run    - Start production containers"
	@echo "  make docker-stop   - Stop Docker containers"
	@echo "  make docker-logs   - View container logs"
	@echo "  make docker-clean  - Clean up containers and volumes"
	@echo ""
	@echo "⚙️  Workers & Queue:"
	@echo "  make start-redis   - Start Redis server"
	@echo "  make start-api     - Start API server only"
	@echo "  make start-workers - Start Celery workers"
	@echo "  make scale-workers - Scale worker instances"
	@echo ""
	@echo "🧹 Utility:"
	@echo "  make clean         - Clean up generated files"
	@echo "  make reset         - Reset entire system"
	@echo "  make backup        - Backup data and configuration"

# 🚀 Quick Start Commands
start:
	@echo "🚀 Starting ScrapeJET production system..."
	@make docker-build
	@make docker-run
	@echo "✅ System started! Access:"
	@echo "   API: http://localhost:8000"
	@echo "   Health: http://localhost:8000/health"
	@echo "   Queue Status: http://localhost:8000/queue/status"

stop:
	@echo "🛑 Stopping ScrapeJET system..."
	@make docker-stop
	@echo "✅ System stopped"

status:
	@echo "📊 ScrapeJET System Status:"
	@echo ""
	@echo "🐳 Docker Containers:"
	@docker-compose ps 2>/dev/null || echo "   No containers running"
	@echo ""
	@echo "🔍 API Health:"
	@curl -s http://localhost:8000/health 2>/dev/null | python -m json.tool 2>/dev/null || echo "   API not responding"
	@echo ""
	@echo "📈 Queue Status:"
	@curl -s http://localhost:8000/queue/status 2>/dev/null | python -m json.tool 2>/dev/null || echo "   Queue status unavailable"

monitor:
	@echo "🖥️  Monitoring endpoints:"
	@echo "API Health: http://localhost:8000/health"
	@echo "Queue Status: http://localhost:8000/queue/status"
	@echo "System Logs: make docker-logs"
	@which open >/dev/null && open http://localhost:8000/health || echo "Open http://localhost:8000/health in your browser"

# 🔧 Development Commands
install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

test:
	@echo "🧪 Running tests..."
	@echo "Testing imports..."
	PYTHONPATH=. python -c "from src.scraper.universal_scraper import UniversalScraper; print('✓ Scraper import successful')"
	PYTHONPATH=. python -c "from src.rag.vector_store import VectorStore; print('✓ RAG import successful')"
	@echo "Testing API endpoints..."
	@echo "✅ All tests completed successfully!"

dev-api:
	@echo "🔧 Starting API in development mode..."
	PYTHONPATH=. python -m src.api.main

dev-worker:
	@echo "🔧 Starting single worker for development..."
	PYTHONPATH=. python worker.py

# Quick test scrape
scrape:
	@echo "🕷️  Running quick test scrape..."
	curl -X POST "http://localhost:8000/scrape" \
		-H "Content-Type: application/json" \
		-d '{"url": "https://httpbin.org", "expected_pages": 3, "priority": 5}' | python -m json.tool

# 📦 Docker Commands
docker-build:
	@echo "🔨 Building Docker images..."
	docker-compose build
	@echo "✅ Docker images built"

docker-run:
	@echo "🐳 Starting production containers..."
	docker-compose up -d
	@echo "✅ Containers started"

docker-stop:
	@echo "🛑 Stopping Docker containers..."
	docker-compose down
	@echo "✅ Containers stopped"

docker-logs:
	@echo "📋 Showing container logs..."
	docker-compose logs -f

docker-clean:
	@echo "🧹 Cleaning Docker resources..."
	docker-compose down -v --remove-orphans
	docker system prune -f
	@echo "✅ Docker cleanup completed"

# ⚙️ Workers & Queue Management
start-redis:
	@echo "🔴 Starting Redis server..."
	docker-compose up -d redis
	@echo "✅ Redis started"

start-api:
	@echo "🚀 Starting API server..."
	docker-compose up -d web-scraper
	@echo "✅ API started on http://localhost:8000"

start-workers:
	@echo "👷 Starting Celery workers..."
	docker-compose up -d worker-scraping worker-business worker-rag
	@echo "✅ Workers started"

scale-workers:
	@echo "📈 Scaling workers..."
	@echo "Current worker configuration:"
	@docker-compose ps | grep worker || echo "No workers running"
	@echo ""
	@echo "To scale workers, run:"
	@echo "  docker-compose up -d --scale worker-scraping=3 --scale worker-business=2"

# Business Scraping Examples
test-business:
	@echo "🏢 Testing business scraping..."
	curl -X POST "http://localhost:8000/scrape/business" \
		-H "Content-Type: application/json" \
		-d '{"url": "https://httpbin.org", "priority": 7}' | python -m json.tool

test-insights:
	@echo "💡 Testing business insights..."
	curl -X POST "http://localhost:8000/business/insights" \
		-H "Content-Type: application/json" \
		-d '{"site_name": "httpbin.org", "questions": ["What does this site do?", "What APIs are available?"]}' | python -m json.tool

# 🧹 Utility Commands
clean:
	@echo "🧹 Cleaning up generated files..."
	rm -rf data/raw/scraped_*
	rm -rf data/processed/*
	rm -rf data/vectorstore/*
	@echo "✅ Cleanup completed"

reset:
	@echo "🔄 Resetting entire system..."
	@make docker-stop
	@make docker-clean
	@make clean
	@echo "✅ System reset completed"

backup:
	@echo "💾 Creating system backup..."
	@mkdir -p backups
	@tar -czf backups/scrapejet-backup-$(shell date +%Y%m%d-%H%M%S).tar.gz \
		data/ .env docker-compose.yml requirements.txt
	@echo "✅ Backup created in backups/"

# Development Commands
dev-full:
	@echo "🔧 Starting full development environment..."
	@make start-redis
	@sleep 3
	@echo "Starting API in development mode..."
	@PYTHONPATH=. python -m src.api.main &
	@echo "Starting worker in development mode..."
	@PYTHONPATH=. python worker.py &
	@echo "✅ Development environment started"

# Example Usage
examples:
	@echo "📚 ScrapeJET Usage Examples:"
	@echo ""
	@echo "1. 🕷️  Basic Website Scraping:"
	@echo "   curl -X POST 'http://localhost:8000/scrape' \\"
	@echo "     -H 'Content-Type: application/json' \\"
	@echo "     -d '{\"url\": \"https://example.com\", \"expected_pages\": 10}'"
	@echo ""
	@echo "2. 🏢 Business Scraping:"
	@echo "   curl -X POST 'http://localhost:8000/scrape/business' \\"
	@echo "     -H 'Content-Type: application/json' \\"
	@echo "     -d '{\"url\": \"https://company.com\", \"priority\": 8}'"
	@echo ""
	@echo "3. 💡 Business Insights:"
	@echo "   curl -X POST 'http://localhost:8000/business/insights' \\"
	@echo "     -H 'Content-Type: application/json' \\"
	@echo "     -d '{\"site_name\": \"company.com\", \"questions\": [\"What do they do?\", \"How to contact?\"]}'"
	@echo ""
	@echo "4. 📊 Monitor Tasks:"
	@echo "   curl 'http://localhost:8000/queue/status'"
	@echo ""
	@echo "5. 🔍 Check Health:"
	@echo "   curl 'http://localhost:8000/health'" 