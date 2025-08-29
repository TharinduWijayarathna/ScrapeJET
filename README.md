# ScrapeJET - Web Scraper with RAG

A powerful web scraper with RAG (Retrieval-Augmented Generation) capabilities for extracting and querying website data using Selenium, Playwright, and AI models.

## Features

- Advanced web scraping with Selenium, Playwright, and Requests
- Intelligent data processing and product extraction
- Queue-based multi-threaded scraping
- JavaScript support for dynamic content
- Smart deduplication and content cleaning
- RAG integration for AI-powered data querying
- REST API with comprehensive endpoints

## Quick Setup

### 1. Environment Configuration

Create a `.env` file:

```bash
# Scraping Configuration
MAX_PAGES=100
MAX_WORKERS=5
REQUEST_TIMEOUT=30
RETRY_COUNT=3
REQUEST_DELAY=1.0

# Advanced Features
USE_SELENIUM=true
USE_PLAYWRIGHT=true
SCROLL_PAGES=true
WAIT_FOR_JS=5

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# LLM Configuration
DEFAULT_LLM_PROVIDER=openai
DEFAULT_OPENAI_MODEL=gpt-3.5-turbo
```

### 2. Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Start API Server

```bash
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Usage

### Health Check
```bash
curl "http://localhost:8000/health"
```

### List Available Sites
```bash
curl "http://localhost:8000/sites"
```

### Scrape a Website
```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "expected_pages": 50,
    "output_format": "json"
  }'
```

### Query Scraped Data
```bash
# General query
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What products are available?",
    "n_results": 5
  }'

# Site-specific query
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What mobile phones are available?",
    "site_name": "example.com",
    "n_results": 5
  }'
```

### Site-Specific Queries
```bash
curl -X POST "http://localhost:8000/ask/site/example.com" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What products are available?",
    "site_name": "example.com",
    "n_results": 10,
    "page_type": "product"
  }'
```

### Site Management
```bash
# Get site information
curl "http://localhost:8000/sites/example.com/info"

# Get site pages
curl "http://localhost:8000/sites/example.com/pages"

# Get filtered pages
curl "http://localhost:8000/sites/example.com/pages?page_type=product"

# Delete site data
curl -X DELETE "http://localhost:8000/sites/example.com"
```

## CLI Usage

```bash
# Scrape a website
python src/cli.py scrape https://example.com --expected-pages 50

# Process raw data
python src/cli.py process data/raw/scraped_example_com_1234567890.json

# Analyze processed data
python src/cli.py analyze data/raw/processed_example_com_1234567890.json
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_PAGES` | 100 | Maximum pages to scrape |
| `MAX_WORKERS` | 5 | Number of concurrent workers |
| `REQUEST_TIMEOUT` | 30 | Request timeout in seconds |
| `RETRY_COUNT` | 3 | Number of retries for failed requests |
| `REQUEST_DELAY` | 1.0 | Delay between requests in seconds |
| `USE_SELENIUM` | true | Enable Selenium for JavaScript-heavy sites |
| `USE_PLAYWRIGHT` | true | Enable Playwright for complex sites |
| `SCROLL_PAGES` | true | Scroll pages to load lazy content |
| `WAIT_FOR_JS` | 5 | Wait time for JavaScript to load (seconds) |
| `OPENAI_API_KEY` | - | Your OpenAI API key |

## Project Structure

```
src/
├── scraper/
│   ├── universal_scraper.py  # Main scraper
│   ├── base_scraper.py       # Base scraper class
│   └── data_processor.py     # Data processing
├── api/
│   └── main.py              # FastAPI application
├── rag/
│   ├── vector_store.py      # Vector store implementation
│   └── llm_interface.py     # LLM interface
└── cli.py                   # Command-line interface

data/
├── raw/                     # Raw scraped data
└── vectorstore/             # Vector store data
```

## License

MIT License