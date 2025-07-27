# Web Scraper with RAG

A comprehensive Python web scraper with RAG (Retrieval-Augmented Generation) capabilities that can scrape any website, extract structured data, and provide intelligent responses using LLMs.

## Features

- **Universal Web Scraping**: Scrape any website with intelligent content extraction
- **Pagination Support**: Automatically detect and handle pagination
- **Multiple Scraping Methods**: Uses requests, Selenium, and Playwright for different site types
- **Product Detection**: Automatically detects and extracts product information
- **Contact Information Extraction**: Extracts emails, phones, and addresses
- **RAG Integration**: Vector-based search with LLM-powered responses
- **Multiple LLM Support**: OpenAI GPT and AWS Bedrock integration
- **Docker Support**: Fully containerized application
- **REST API**: FastAPI-based API for easy integration
- **CLI Interface**: Command-line tool for quick usage

## Architecture

```
web-scraper/
├── src/
│   ├── scraper/          # Web scraping modules
│   │   ├── base_scraper.py
│   │   └── universal_scraper.py
│   ├── rag/             # RAG functionality
│   │   ├── vector_store.py
│   │   └── llm_interface.py
│   └── api/             # FastAPI application
│       └── main.py
├── data/                # Data storage
│   ├── raw/            # Raw scraped data
│   ├── processed/      # Processed data
│   └── vectorstore/    # Vector database
├── Dockerfile          # Docker configuration
├── docker-compose.yml  # Docker Compose setup
└── requirements.txt    # Python dependencies
```

## Quick Start

### Using Docker (Recommended)

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd web-scraper
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Run with Docker Compose**:
   ```bash
   docker-compose up --build
   ```

4. **Access the API**:
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

### Using Python directly

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables**:
   ```bash
   export OPENAI_API_KEY="your_openai_api_key"
   # or for AWS Bedrock
   export AWS_ACCESS_KEY_ID="your_aws_key"
   export AWS_SECRET_ACCESS_KEY="your_aws_secret"
   ```

3. **Run the API**:
   ```bash
   python -m src.api.main
   ```

## Usage

### Command Line Interface

```bash
# Basic scraping
python src/cli.py https://example.com

# Scrape with custom settings
python src/cli.py https://example.com --max-pages 50 --output-format json

# Scrape and start interactive query mode
python src/cli.py https://example.com --interactive

# Single query
python src/cli.py https://example.com --query "What products are available?"

# Use AWS Bedrock
python src/cli.py https://example.com --llm-provider bedrock --interactive
```

### API Usage

#### 1. Scrape a Website

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "max_pages": 100,
    "output_format": "both",
    "llm_provider": "openai"
  }'
```

#### 2. Query the RAG System

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What products are available?",
    "n_results": 5
  }'
```

#### 3. Check Data Status

```bash
curl "http://localhost:8000/data/status"
```

#### 4. Clear Data

```bash
curl -X DELETE "http://localhost:8000/data/clear"
```

### Python API Usage

```python
import requests

# Scrape website
scrape_response = requests.post("http://localhost:8000/scrape", json={
    "url": "https://example.com",
    "max_pages": 50,
    "llm_provider": "openai"
})

# Query RAG system
query_response = requests.post("http://localhost:8000/query", json={
    "question": "What are the main features of this website?",
    "n_results": 3
})

print(query_response.json()["answer"])
```

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# AWS Bedrock Configuration (optional)
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
AWS_DEFAULT_REGION=us-east-1

# Application Configuration
MAX_PAGES=100
CHUNK_SIZE=1000
LOG_LEVEL=INFO
```

### LLM Providers

#### OpenAI
- Models: `gpt-3.5-turbo`, `gpt-4`, `gpt-4-turbo`
- Requires: OpenAI API key

#### AWS Bedrock
- Models: `anthropic.claude-v2`, `anthropic.claude-3`, `amazon.titan-text-express-v1`
- Requires: AWS credentials with Bedrock access

## Features in Detail

### Web Scraping

The scraper uses multiple strategies to handle different types of websites:

1. **Requests**: Fast scraping for static sites
2. **Selenium**: JavaScript-heavy sites with Chrome
3. **Playwright**: Complex dynamic sites

#### Content Extraction

- **General Content**: Titles, descriptions, main content
- **Products**: Names, prices, descriptions, images, links
- **Contact Information**: Emails, phone numbers, addresses
- **Links**: Internal and external links
- **Images**: Image URLs and metadata

#### Pagination Detection

Automatically detects common pagination patterns:
- `?page=2`
- `?p=2`
- `/page/2`
- Numeric URLs

### RAG System

#### Vector Store
- Uses ChromaDB for vector storage
- Sentence transformers for embeddings
- Configurable chunk size and overlap

#### LLM Integration
- Context-aware responses
- Multiple model support
- Configurable temperature and tokens

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/scrape` | POST | Scrape a website |
| `/query` | POST | Query the RAG system |
| `/data/status` | GET | Get data status |
| `/data/clear` | DELETE | Clear all data |
| `/rag/reinitialize` | POST | Reinitialize RAG system |

## Data Formats

### JSON Output
```json
{
  "url": "https://example.com",
  "title": "Example Website",
  "description": "Website description",
  "content": "Main content text...",
  "products": [
    {
      "name": "Product Name",
      "price": "$99.99",
      "description": "Product description",
      "image": "https://example.com/image.jpg",
      "link": "https://example.com/product"
    }
  ],
  "contact_info": {
    "emails": ["contact@example.com"],
    "phones": ["+1-555-1234"],
    "address": "123 Main St, City, State"
  },
  "links": ["https://example.com/page1"],
  "images": ["https://example.com/image1.jpg"]
}
```

### Markdown Output
```markdown
**url:** https://example.com
**title:** Example Website
**description:** Website description
**content:** Main content text...

**products:**
- Product: Product Name | Price: $99.99 | Description: Product description

**contact_info:**
- emails: contact@example.com
- phones: +1-555-1234
- address: 123 Main St, City, State
```

## Examples

### E-commerce Scraping
```bash
# Scrape an e-commerce site
python src/cli.py https://shop.example.com --interactive

# Query about products
> What products are available under $50?
> What are the most expensive items?
> Are there any discounts or sales?
```

### Business Website Analysis
```bash
# Scrape a business website
python src/cli.py https://company.example.com --interactive

# Query about the business
> What services does this company offer?
> What are their contact details?
> What is their main value proposition?
```

### News/Blog Analysis
```bash
# Scrape a news site
python src/cli.py https://news.example.com --interactive

# Query about content
> What are the main topics covered?
> What are the latest articles?
> Who are the main authors?
```

## Troubleshooting

### Common Issues

1. **Chrome/Selenium Issues**:
   - Ensure Chrome is installed in Docker
   - Check ChromeDriver version compatibility

2. **API Key Issues**:
   - Verify API keys are set correctly
   - Check API quotas and billing

3. **Memory Issues**:
   - Reduce `max_pages` for large sites
   - Increase Docker memory limits

4. **Rate Limiting**:
   - Add delays between requests
   - Use proxy rotation (not implemented)

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python src/cli.py https://example.com --log-level DEBUG
```

## Development

### Project Structure
```
src/
├── scraper/          # Web scraping logic
├── rag/             # RAG and vector operations
├── api/             # FastAPI application
└── cli.py          # Command-line interface
```

### Adding New Features

1. **Custom Scrapers**: Extend `BaseScraper`
2. **New LLM Providers**: Implement `LLMInterface`
3. **Additional Data Formats**: Add to `UniversalScraper`

### Testing

```bash
# Run tests (when implemented)
pytest tests/

# Manual testing
python src/cli.py https://httpbin.org --max-pages 1
```

## License

This project is licensed under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

For issues and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the API documentation at `/docs`
