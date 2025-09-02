# ScrapeJET Production Queue System

## Overview

ScrapeJET now includes a production-grade queue system using **Celery** and **Redis** for handling concurrent scraping requests. This system provides:

- **Concurrent Processing**: Multiple workers can process scraping tasks simultaneously
- **Queue Management**: Tasks are queued and processed efficiently with priority support
- **Business Intelligence**: Specialized endpoints for business page scraping and insights
- **Real-time Monitoring**: Queue status and worker monitoring via API endpoints
- **Scalability**: Easy horizontal scaling of workers
- **Fault Tolerance**: Task retries and failure handling

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI API   │────│     Redis       │────│ Celery Workers  │
│                 │    │   (Message      │    │                 │
│ - HTTP Endpoints│    │    Broker)      │    │ - Scraping      │
│ - Task Creation │    │                 │    │ - Business      │
│ - Status Check  │    │                 │    │ - RAG Processing│
│ - Queue Monitor │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Services

### 1. API Server (`web-scraper`)
- **Port**: 8000
- **Purpose**: Main API endpoints for task creation and monitoring
- **Health Check**: `http://localhost:8000/health`

### 2. Redis (`redis`)
- **Port**: 6379
- **Purpose**: Message broker and result backend
- **Memory**: 512MB with LRU eviction policy

### 3. Worker Services
#### Scraping Worker (`worker-scraping`)
- **Queue**: `scraping`
- **Purpose**: General website scraping tasks
- **Resources**: 4GB RAM, 2 CPU cores

#### Business Worker (`worker-business`)
- **Queue**: `business`
- **Purpose**: Business page scraping (about, contact, terms, etc.)
- **Resources**: 3GB RAM, 1.5 CPU cores

#### RAG Worker (`worker-rag`)
- **Queue**: `rag`
- **Purpose**: RAG processing and business insights
- **Resources**: 3GB RAM, 1 CPU core

## New API Endpoints

### General Scraping
```bash
# Start a scraping task
POST /scrape
{
    "url": "https://example.com",
    "expected_pages": 100,
    "output_format": "json",
    "priority": 5
}

# Get task progress
GET /scrape/{job_id}/progress

# Get task result
GET /scrape/{job_id}/result

# Cancel task
DELETE /scrape/{job_id}
```

### Business Scraping
```bash
# Scrape business pages
POST /scrape/business
{
    "url": "https://company.com",
    "pages_to_scrape": ["/", "/about", "/contact", "/terms"],
    "priority": 7
}

# Get business insights
POST /business/insights
{
    "site_name": "company.com",
    "questions": [
        "What does this company do?",
        "How can I contact them?",
        "Where are they located?"
    ]
}

# Get insights result
GET /business/insights/{task_id}
```

### Queue Management
```bash
# Check queue status
GET /queue/status

# System health
GET /health
```

## Deployment

### Quick Start
```bash
# 1. Clone the repository
git clone <repository-url>
cd ScrapeJET

# 2. Set environment variables
cp .env.example .env
# Edit .env with your configuration

# 3. Start all services
docker-compose up -d

# 4. Check status
curl http://localhost:8000/health
curl http://localhost:8000/queue/status  # Queue status
```

### Environment Variables
```env
# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # Optional

# Scraping Configuration
MAX_PAGES=100
MAX_WORKERS=5
REQUEST_TIMEOUT=30
REQUEST_DELAY=1.0

# AWS Configuration (Optional)
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_DEFAULT_REGION=us-east-1
```

### Scaling Workers
```bash
# Scale specific worker types
docker-compose up -d --scale worker-scraping=3
docker-compose up -d --scale worker-business=2
docker-compose up -d --scale worker-rag=2

# Or edit docker-compose.yml and add:
# deploy:
#   replicas: 3
```

## Usage Examples

### 1. Basic Website Scraping
```python
import requests

# Start scraping
response = requests.post("http://localhost:8000/scrape", json={
    "url": "https://example.com",
    "expected_pages": 50,
    "priority": 5
})
job_id = response.json()["job_id"]

# Monitor progress
progress = requests.get(f"http://localhost:8000/scrape/{job_id}/progress")
print(progress.json())

# Get result when completed
result = requests.get(f"http://localhost:8000/scrape/{job_id}/result")
print(result.json())
```

### 2. Business Intelligence Scraping
```python
import requests
import time

# Scrape business pages
response = requests.post("http://localhost:8000/scrape/business", json={
    "url": "https://company.com",
    "priority": 8
})
job_id = response.json()["job_id"]

# Wait for completion
while True:
    progress = requests.get(f"http://localhost:8000/scrape/{job_id}/progress")
    status = progress.json()["status"]
    if status == "completed":
        break
    time.sleep(5)

# Get business insights
insights_response = requests.post("http://localhost:8000/business/insights", json={
    "site_name": "company.com",
    "questions": [
        "What does this company do?",
        "What are their main services?",
        "How can I contact them?"
    ]
})
insights_task_id = insights_response.json()["task_id"]

# Get insights result
insights_result = requests.get(f"http://localhost:8000/business/insights/{insights_task_id}")
print(insights_result.json())
```

### 3. Queue Monitoring
```python
import requests

# Check system health
health = requests.get("http://localhost:8000/health")
print("System Status:", health.json())

# Check queue status
queue_status = requests.get("http://localhost:8000/queue/status")
print("Queue Status:", queue_status.json())
```

## Monitoring and Debugging

### API Monitoring
Use the built-in API endpoints for monitoring:
- **Health Check**: `http://localhost:8000/health` - System status and worker count
- **Queue Status**: `http://localhost:8000/queue/status` - Active tasks and queue lengths
- **Task Progress**: `http://localhost:8000/scrape/{job_id}/progress` - Individual task status

### Logs
```bash
# View API logs
docker-compose logs -f web-scraper

# View worker logs
docker-compose logs -f worker-scraping
docker-compose logs -f worker-business
docker-compose logs -f worker-rag

# View Redis logs
docker-compose logs -f redis
```

### Health Checks
```bash
# API health
curl http://localhost:8000/health

# Redis health
docker-compose exec redis redis-cli ping

# Worker status
curl http://localhost:8000/queue/status
```

## Performance Optimization

### Resource Allocation
- **API Server**: 2GB RAM, 1 CPU (handles HTTP requests)
- **Scraping Worker**: 4GB RAM, 2 CPU (browser automation)
- **Business Worker**: 3GB RAM, 1.5 CPU (targeted scraping)
- **RAG Worker**: 3GB RAM, 1 CPU (AI processing)
- **Redis**: 512MB RAM (message queue)

### Scaling Guidelines
1. **High Scraping Load**: Scale `worker-scraping`
2. **Business Intelligence**: Scale `worker-business` and `worker-rag`
3. **Memory Issues**: Increase worker memory limits
4. **Queue Backup**: Add more workers of the appropriate type

### Task Priorities
- **1-3**: Low priority (background tasks)
- **4-6**: Normal priority (default)
- **7-9**: High priority (urgent tasks)

## Troubleshooting

### Common Issues

1. **Workers Not Starting**
   ```bash
   # Check Redis connection
   docker-compose logs redis
   
   # Restart workers
   docker-compose restart worker-scraping worker-business worker-rag
   ```

2. **Tasks Stuck in Queue**
   ```bash
   # Check worker status
   curl http://localhost:8000/queue/status
   
   # Scale workers if needed
   docker-compose up -d --scale worker-scraping=2
   ```

3. **Memory Issues**
   ```bash
   # Monitor memory usage
   docker stats
   
   # Adjust memory limits in docker-compose.yml
   ```

4. **Redis Connection Issues**
   ```bash
   # Check Redis status
   docker-compose exec redis redis-cli ping
   
   # Restart Redis
   docker-compose restart redis
   ```

### Task States
- **PENDING**: Task waiting in queue
- **PROGRESS**: Task being processed
- **SUCCESS**: Task completed successfully
- **FAILURE**: Task failed with error
- **REVOKED**: Task cancelled by user

## Production Considerations

### Security
1. Use Redis AUTH if exposed
2. Configure firewall rules
3. Use HTTPS for API access
4. Implement API authentication for production

### Backup
1. **Redis Data**: Persistent volume with backups
2. **Scraped Data**: Regular backup of `/app/data`
3. **Configuration**: Version control `.env` and `docker-compose.yml`

### Monitoring
1. **Health Checks**: Automated monitoring of all services
2. **Resource Usage**: CPU, memory, and disk monitoring
3. **Queue Metrics**: Track task throughput and failure rates
4. **Alerts**: Set up alerts for worker failures or queue backups

This queue system transforms ScrapeJET into a production-ready scraping platform capable of handling multiple concurrent requests with proper task management and monitoring.
