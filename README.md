# Super Web Scraper with RAG - Advanced Version

A super-powered web scraper with advanced capabilities including Selenium, Playwright, and RAG (Retrieval-Augmented Generation) for extracting and querying any website data. **Now with intelligent data processing and structured product extraction!**

## ✅ **System Status: FULLY OPERATIONAL**

The system is currently running with:
- ✅ **API Server**: Running on http://localhost:8000
- ✅ **RAG System**: OpenAI GPT-3.5-turbo integration
- ✅ **Vector Store**: ChromaDB with 76 chunks of processed data
- ✅ **Data Processing**: Intelligent product extraction and categorization
- ✅ **Real Data**: 138 products from Celltronics.lk successfully processed

## Features

- **Super Web Scraping**: Advanced scraping with Selenium, Playwright, and Requests
- **Intelligent Data Processing**: Automatic product extraction, categorization, and structuring
- **Queue-based Workers**: Efficient multi-threaded scraping with proper queue management
- **JavaScript Support**: Handle dynamic content and SPAs
- **Advanced Content Extraction**: Extract images, forms, scripts, and metadata
- **Smart Deduplication**: Remove duplicate content automatically
- **RAG Integration**: Query scraped data using AI models with context-aware responses
- **Environment-based Configuration**: All settings via environment variables
- **Comprehensive API**: Full-featured REST API with site-specific queries
- **CLI Interface**: Easy command-line usage with interactive mode

## 🚀 **Quick Start**

### 1. Setup Environment

Create a `.env` file with your configuration:

```bash
# Scraping Configuration
MAX_PAGES=100
MAX_WORKERS=5
REQUEST_TIMEOUT=30
RETRY_COUNT=3
REQUEST_DELAY=1.0

# Advanced Scraping Features
USE_SELENIUM=true
USE_PLAYWRIGHT=true
SCROLL_PAGES=true
SCREENSHOT_PAGES=false
WAIT_FOR_JS=5

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Optional: AWS Bedrock
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
AWS_DEFAULT_REGION=us-east-1

# LLM Configuration
DEFAULT_LLM_PROVIDER=openai
DEFAULT_OPENAI_MODEL=gpt-3.5-turbo
DEFAULT_BEDROCK_MODEL=anthropic.claude-v2

# Logging
LOG_LEVEL=INFO
```

### 2. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Start the API Server

```bash
# Start the API server
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Basic Usage

#### CLI Usage

```bash
# Scrape a website with data processing
python src/cli.py scrape https://example.com --expected-pages 50

# Process raw scraped data into structured format
python src/cli.py process data/raw/scraped_example_com_1234567890.json

# Analyze processed data
python src/cli.py analyze data/raw/processed_example_com_1234567890.json
```

#### API Usage

```bash
# Health check
curl "http://localhost:8000/health"

# List available sites
curl "http://localhost:8000/sites"

# Scrape a website
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "expected_pages": 50}'

# Query scraped data with RAG
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What products does this site offer?", "site_name": "example.com"}'
```

## 📊 **Current System Data**

### Celltronics.lk (Live Example)
- **Products**: 138 products successfully extracted
- **Categories**: 5 categories (Mobile Phones, JBL Speakers, Headphones, Earbuds, Power Banks)
- **Price Range**: Rs. 9,990 - Rs. 529,900
- **Vector Chunks**: 76 unique chunks in RAG system
- **Data Quality**: Structured product information with prices, discounts, and specifications

### Sample Queries Working
```bash
# What mobile phones are available?
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What mobile phones are available?", "site_name": "celltronics.lk"}'

# What are the prices of Samsung phones?
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the prices of Samsung phones?", "site_name": "celltronics.lk"}'

# Show me JBL speakers
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Show me JBL speakers", "site_name": "celltronics.lk"}'
```

## 🔧 **Data Processing Pipeline**

The system now includes intelligent data processing:

1. **Raw Scraping**: Extract unstructured content from websites
2. **Data Processing**: Convert raw data into structured product information
3. **Product Extraction**: Identify products, prices, discounts, and specifications
4. **Categorization**: Organize products by categories
5. **RAG Integration**: Load structured data into vector store for intelligent querying

### Processing Features
- **Product Pattern Recognition**: Regex-based product name and price extraction
- **Category Detection**: Automatic categorization of products
- **Price Analysis**: Current prices, original prices, and discount calculations
- **Specification Parsing**: Extract product specifications and features
- **Data Cleaning**: Remove boilerplate and irrelevant content

## API Endpoints

### Core Endpoints

- `GET /health` - System health check
- `GET /sites` - List available sites with statistics
- `POST /scrape` - Scrape a website with expected pages
- `POST /query` - Query scraped data with RAG
- `DELETE /sites/{site_name}` - Clear data for a specific site

### Site-Specific RAG Endpoints

- `POST /ask/site/{site_name}` - Ask questions about a specific site with filtering
- `GET /sites/{site_name}/info` - Get detailed information about a site
- `GET /sites/{site_name}/pages` - Get pages from a site with optional filtering

### Example Requests

```bash
# Scrape a website
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "expected_pages": 50, "output_format": "json"}'

# Query with site-specific context
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the main features?", "site_name": "example.com", "n_results": 5}'

# Ask site-specific questions with filtering
curl -X POST "http://localhost:8000/ask/site/example.com" \
  -H "Content-Type: application/json" \
  -d '{"question": "What products are available?", "page_type": "product", "n_results": 10}'
```

## CLI Commands

### New CLI Structure

```bash
# Scrape websites
python src/cli.py scrape <url> [options]

# Process raw data
python src/cli.py process <input_file> [options]

# Analyze processed data
python src/cli.py analyze <input_file> [options]
```

### Examples

```bash
# Scrape a website
python src/cli.py scrape https://example.com --expected-pages 30

# Process scraped data
python src/cli.py process data/raw/scraped_example_com_1234567890.json

# Analyze processed data
python src/cli.py analyze data/raw/processed_example_com_1234567890.json
```

## Configuration

All configuration is done through environment variables:

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
| `SCREENSHOT_PAGES` | false | Take screenshots of pages |
| `WAIT_FOR_JS` | 5 | Wait time for JavaScript to load (seconds) |
| `OPENAI_API_KEY` | - | Your OpenAI API key |
| `LOG_LEVEL` | INFO | Logging level |

## Advanced Data Processing

The super scraper extracts comprehensive data:

- **Page URLs** - All discovered pages with intelligent filtering
- **Content** - Main text content with advanced cleaning
- **Titles** - Page titles and headings
- **Metadata** - Meta tags, Open Graph, Twitter Cards, and Schema.org data
- **Images** - Image URLs, alt text, and dimensions
- **Forms** - Form actions, methods, and input fields
- **Scripts** - JavaScript files and inline scripts
- **Styles** - CSS files and stylesheets
- **Links** - Internal links with JavaScript link extraction
- **Products** - Structured product information with prices and specifications
- **Categories** - Automatic product categorization
- **Advanced Features** - Screenshots, scroll detection, lazy loading support

Data is automatically deduplicated, cleaned, organized by site, and processed for RAG processing.

## RAG Integration

The system uses:

- **Vector Store** - ChromaDB for semantic search
- **LLM Interface** - OpenAI GPT-3.5-turbo or AWS Bedrock
- **Site-wise Organization** - Data organized by domain
- **Context Retrieval** - Relevant context for queries
- **Conversation History** - Maintains context across queries
- **Response Caching** - Intelligent caching for similar queries

## Development

### Project Structure

```
src/
├── scraper/
│   ├── universal_scraper.py  # Main scraper
│   ├── base_scraper.py       # Base scraper class
│   └── data_processor.py     # Data processing and structuring
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

### Testing

```bash
# Test scraper
python test_scraper.py

# Test RAG system
python test_rag.py

# Test API endpoints
curl "http://localhost:8000/health"
```

## Docker

```bash
# Build and run with Docker
docker build -t web-scraper .
docker run -p 8000:8000 web-scraper
```

## License

MIT License
