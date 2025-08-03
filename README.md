# 🚀 Universal Web Scraper with Enhanced RAG

A powerful, multithreaded web scraper with intelligent RAG (Retrieval-Augmented Generation) capabilities and **automatic data optimization**.

## ✨ Key Features

### 🔄 **Multithreaded Scraping**
- Parallel processing for faster data extraction
- Configurable worker threads (default: 5-10 workers)
- Intelligent retry mechanisms with exponential backoff
- Queue-based URL processing for optimal performance

### 🧠 **Enhanced RAG System**
- **Conversation Tracking**: Maintains context across multiple queries
- **Smart Caching**: Avoids repetitive responses for similar queries
- **Precision Filtering**: Advanced relevance scoring and content deduplication
- **Response Diversity**: Prevents repetitive answers with intelligent tracking
- **Context Enhancement**: Better prompt engineering for more accurate responses

### 🎯 **Universal Compatibility**
- Works with any website type (e-commerce, news, corporate, educational)
- Multiple scraping methods (requests, Selenium, Playwright)
- Intelligent content extraction and optimization
- Site-specific data organization

### 📊 **Automatic Data Optimization**
- **Content Deduplication**: Removes duplicate pages and content automatically
- **Product Deduplication**: Eliminates duplicate product entries based on name and price
- **Contact Info Deduplication**: Ensures unique contact details
- **Smart Content Cleaning**: Removes boilerplate text and excessive whitespace
- **Real-time Optimization Stats**: Tracks optimization metrics during scraping
- **Hash-based Deduplication**: Uses MD5 hashes for efficient duplicate detection

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd web-scraper

# Start the API server
docker-compose up -d

# Or using Makefile
make docker-run
```

### Local Installation

```bash
# Clone the repository
git clone https://github.com/TharinduWijayarathna/ScrapeJET.git
cd ScrapeJET

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

# Start the API server
source venv/bin/activate
PYTHONPATH=. python -m src.api.main
```

## 📡 API Endpoints

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information and available endpoints |
| `/health` | GET | Health check |
| `/scrape` | POST | Scrape a website with automatic optimization |
| `/query` | POST | Query the RAG system |
| `/query/enhanced` | POST | Enhanced query with conversation context |
| `/sites` | GET | Get available sites |
| `/conversation` | GET | Get conversation history |
| `/conversation` | DELETE | Clear conversation history |
| `/cache/stats` | GET | Get cache statistics |
| `/cache` | DELETE | Clear query cache |
| `/data/optimization` | GET | Get optimization statistics |

## 🎯 Curl Examples

### Scrape a Website with Automatic Optimization

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "max_pages": 50,
    "max_workers": 5,
    "output_format": "json"
  }'
```

**Response includes optimization statistics:**
```json
{
  "message": "Successfully scraped 10 pages from https://example.com with 15.2% optimization",
  "files": {
    "json": "data/raw/scraped_https_example_com.json",
    "optimization_stats": "data/raw/scraped_https_example_com_optimization_stats.json"
  },
  "total_pages": 10,
  "optimization_stats": {
    "total_pages_scraped": 10,
    "duplicate_pages_skipped": 2,
    "duplicate_content_removed": 3,
    "duplicate_products_removed": 1,
    "duplicate_contacts_removed": 0,
    "content_cleaned": 10,
    "optimization_ratio": 15.2
  }
}
```

### Query the RAG System

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What products does this website offer?",
    "n_results": 5
  }'
```

### Enhanced Query with Conversation Context

```bash
curl -X POST "http://localhost:8000/query/enhanced" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Summarize the key information",
    "n_results": 5
  }'
```

### Site-Specific Query

```bash
curl -X POST "http://localhost:8000/query/site/example.com" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the contact details?",
    "n_results": 5
  }'
```

### Get Conversation History

```bash
curl -X GET "http://localhost:8000/conversation"
```

### Clear Conversation History

```bash
curl -X DELETE "http://localhost:8000/conversation"
```

### Get Cache Statistics

```bash
curl -X GET "http://localhost:8000/cache/stats"
```

### Get Available Sites

```bash
curl -X GET "http://localhost:8000/sites"
```

### Get Optimization Statistics

```bash
curl -X GET "http://localhost:8000/data/optimization"
```

## 🔧 Configuration

### Environment Variables

```bash
# Required for RAG functionality
OPENAI_API_KEY=your_openai_api_key

# Optional settings
LOG_LEVEL=INFO
MAX_PAGES=50
MAX_WORKERS=5
```

### Docker Configuration

The default `docker-compose.yml` includes:
- Resource limits (2GB memory, 1 CPU)
- Health checks
- Logging with rotation
- Persistent data volumes
- Non-root user for security

## 🎯 Use Cases

### E-commerce Analysis
```bash
# Scrape product catalog with automatic deduplication
curl -X POST "http://localhost:8000/scrape" \
  -d '{"url": "https://shop.example.com", "max_pages": 100}'

# Query product information
curl -X POST "http://localhost:8000/query" \
  -d '{"question": "What are the most expensive products?"}'
```

### News/Content Analysis
```bash
# Scrape news website with content optimization
curl -X POST "http://localhost:8000/scrape" \
  -d '{"url": "https://news.example.com", "max_pages": 50}'

# Analyze content
curl -X POST "http://localhost:8000/query" \
  -d '{"question": "What are the main topics covered?"}'
```

### Corporate Website Analysis
```bash
# Scrape company website with contact deduplication
curl -X POST "http://localhost:8000/scrape" \
  -d '{"url": "https://company.example.com", "max_pages": 30}'

# Extract business information
curl -X POST "http://localhost:8000/query" \
  -d '{"question": "What are the company main services?"}'
```

## 🚀 Live Testing

### Test on Live Server

```bash
# Replace with your live URL
curl -X POST "https://scraper.tharindu.xyz/scrape" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://httpbin.org","max_pages":3,"max_workers":2}'

curl -X POST "https://scraper.tharindu.xyz/query" \
  -H "Content-Type: application/json" \
  -d '{"question":"What information is available?","n_results":5}'
```

## 🔧 Troubleshooting

### Common Issues

1. **"Bad Gateway" Error**
   - Check if API server is running
   - Verify Docker container health
   - Check logs: `docker-compose logs -f`

2. **RAG Not Working**
   - Ensure `OPENAI_API_KEY` is set
   - Check API key validity
   - Verify internet connectivity

3. **Slow Responses**
   - Reduce `max_workers` for stability
   - Check server resources
   - Monitor cache statistics

4. **Low Optimization Ratio**
   - This is normal for small sites with unique content
   - Larger sites with similar pages will show higher optimization
   - Check optimization stats in the response

### Debug Commands
```bash
# Check API health
curl -X GET "http://localhost:8000/health"

# View logs
docker-compose logs -f

# Check data status
curl -X GET "http://localhost:8000/data/status"

# Check optimization stats
curl -X GET "http://localhost:8000/data/optimization"
```

## 📄 License

This project is licensed under the MIT License.

---

**🎉 Ready to scrape and analyze any website with intelligent RAG capabilities and automatic optimization!**
