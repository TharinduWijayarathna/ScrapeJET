# Web Scraper with RAG

A comprehensive Python web scraper with RAG (Retrieval-Augmented Generation) capabilities that can scrape any website, extract structured data, and provide intelligent responses using LLMs.

## 🚀 Features

- **Universal Web Scraping**: Scrape any website with intelligent content extraction
- **Multithreaded Scraping**: Parallel processing for faster scraping with configurable worker threads
- **Pagination Support**: Automatically detect and handle pagination
- **Multiple Scraping Methods**: Uses requests, Selenium, and Playwright for different site types
- **Product Detection**: Automatically detects and extracts product information
- **Contact Information Extraction**: Extracts emails, phones, and addresses
- **RAG Integration**: Vector-based search with LLM-powered responses
- **Multiple LLM Support**: OpenAI GPT and AWS Bedrock integration
- **Docker Support**: Fully containerized application
- **REST API**: FastAPI-based API for easy integration
- **CLI Interface**: Command-line tool for quick usage

## 📋 Requirements

- **Python 3.12+** (recommended) or Python 3.11
- **Chrome/Chromium** (for Selenium scraping)
- **Git** (for cloning)
- **Virtual Environment** (recommended)

## 🛠️ Installation

### Method 1: Direct Installation (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/TharinduWijayarathna/ScrapeJET.git
   cd web-scraper
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install system dependencies** (Linux/Ubuntu):
   ```bash
   sudo apt update
   sudo apt install -y swig build-essential libopenblas-dev
   ```

4. **Install Python dependencies**:
   ```bash
   pip install --upgrade setuptools wheel
   pip install -r requirements.txt
   ```

5. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

### Method 2: Docker Installation

1. **Clone and navigate**:
   ```bash
   git clone https://github.com/TharinduWijayarathna/ScrapeJET.git
   cd web-scraper
   ```

2. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Run with Docker Compose**:
   ```bash
   docker-compose up --build
   ```

## 🚀 Quick Start

### Basic Usage

```bash
# Activate virtual environment
source venv/bin/activate

# Basic scraping (replace with your actual project path)
PYTHONPATH=/home/thari/office/web-scraper python src/cli.py https://example.com

# Scrape with options
PYTHONPATH=/home/thari/office/web-scraper python src/cli.py https://example.com --max-pages 50 --output-format json
```

### Interactive Mode

```bash
# Scrape and start interactive querying
PYTHONPATH=/home/thari/office/web-scraper python src/cli.py https://example.com --interactive

# Example queries:
# > What products are available?
# > What are the contact details?
# > What services do they offer?
```

## 📖 Usage Guide

### Command Line Interface

#### Basic Scraping
```bash
# Simple scraping
PYTHONPATH=/home/thari/office/web-scraper python src/cli.py https://example.com

# Limit pages
PYTHONPATH=/home/thari/office/web-scraper python src/cli.py https://example.com --max-pages 10

# Use multithreading for faster scraping
PYTHONPATH=/home/thari/office/web-scraper python src/cli.py https://example.com --max-workers 20

# Choose output format
PYTHONPATH=/home/thari/office/web-scraper python src/cli.py https://example.com --output-format json
```

#### RAG Features
```bash
# Interactive querying
PYTHONPATH=/home/thari/office/web-scraper python src/cli.py https://example.com --interactive

# Single query
PYTHONPATH=/home/thari/office/web-scraper python src/cli.py https://example.com --query "What products do they sell?"

# Use different LLM providers
PYTHONPATH=/home/thari/office/web-scraper python src/cli.py https://example.com --llm-provider openai --interactive
PYTHONPATH=/home/thari/office/web-scraper python src/cli.py https://example.com --llm-provider bedrock --interactive
```

#### Advanced Options
```bash
# Debug mode
PYTHONPATH=/home/thari/office/web-scraper python src/cli.py https://example.com --log-level DEBUG

# Custom LLM model
PYTHONPATH=/home/thari/office/web-scraper python src/cli.py https://example.com --llm-model gpt-4 --interactive
```

### Available Options

| Option | Description | Default |
|--------|-------------|---------|
| `--max-pages` | Maximum pages to scrape | 100 |
| `--max-workers` | Maximum number of worker threads for parallel scraping | 10 |
| `--output-format` | Output format (json/markdown/both) | both |
| `--llm-provider` | LLM provider (openai/bedrock) | openai |
| `--llm-model` | Specific LLM model | gpt-3.5-turbo |
| `--interactive` | Start interactive query mode | False |
| `--query` | Single query to run | None |
| `--log-level` | Logging level | INFO |

### API Usage

#### Start the API Server
```bash
# Activate virtual environment
source venv/bin/activate

# Start API server
PYTHONPATH=/home/thari/office/web-scraper python -m src.api.main
```

#### API Endpoints

1. **Scrape Website**:
   ```bash
   curl -X POST "http://localhost:8000/scrape" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://example.com",
       "max_pages": 100,
       "max_workers": 10,
       "output_format": "both"
     }'
   ```

2. **Query RAG System**:
   ```bash
   curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{
       "question": "What products are available?",
       "n_results": 5
     }'
   ```

3. **Check Status**:
   ```bash
   curl "http://localhost:8000/health"
   ```

## 🔧 Configuration

### Environment Variables

Create a `.env` file:

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
- **Models**: `gpt-3.5-turbo`, `gpt-4`, `gpt-4-turbo`
- **Setup**: Get API key from [OpenAI Platform](https://platform.openai.com/)
- **Cost**: Pay-per-token usage

#### AWS Bedrock
- **Models**: `anthropic.claude-v2`, `anthropic.claude-3`, `amazon.titan-text-express-v1`
- **Setup**: AWS credentials with Bedrock access
- **Cost**: AWS pricing model

## 📊 Output Formats

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

## 🎯 Use Cases

### E-commerce Scraping
```bash
# Scrape product catalog
PYTHONPATH=/home/thari/office/web-scraper python src/cli.py https://shop.example.com --interactive

# Example queries:
# > What products are available under $50?
# > What are the most expensive items?
# > Are there any discounts or sales?
# > What categories of products do they sell?
```

### Business Website Analysis
```bash
# Scrape company website
PYTHONPATH=/home/thari/office/web-scraper python src/cli.py https://company.example.com --interactive

# Example queries:
# > What services does this company offer?
# > What are their contact details?
# > What is their main value proposition?
# > Who are the key team members?
```

### News/Blog Analysis
```bash
# Scrape news site
PYTHONPATH=/home/thari/office/web-scraper python src/cli.py https://news.example.com --interactive

# Example queries:
# > What are the main topics covered?
# > What are the latest articles?
# > Who are the main authors?
# > What are the trending stories?
```

## 🐛 Troubleshooting

### Common Issues

#### 1. **ModuleNotFoundError: No module named 'src'**
```bash
# Solution: Set PYTHONPATH to your actual project directory
export PYTHONPATH=/home/thari/office/web-scraper
# or
PYTHONPATH=/home/thari/office/web-scraper python src/cli.py https://example.com
```

#### 2. **ModuleNotFoundError: No module named 'loguru'**
```bash
# Solution: Activate virtual environment
source venv/bin/activate
```

#### 3. **faiss-cpu build errors**
```bash
# Solution: Install system dependencies
sudo apt update
sudo apt install -y swig build-essential libopenblas-dev

# Then reinstall
pip install faiss-cpu --no-build-isolation
```

#### 4. **Chrome/Selenium Issues**
```bash
# Install Chrome
sudo apt install -y google-chrome-stable

# Or use Docker for consistent environment
docker-compose up --build
```

#### 5. **API Key Issues**
```bash
# Check environment variables
echo $OPENAI_API_KEY

# Set in .env file
echo "OPENAI_API_KEY=your_key_here" >> .env
```

### Debug Mode

```bash
# Enable debug logging
PYTHONPATH=/home/thari/office/web-scraper python src/cli.py https://example.com --log-level DEBUG
```

### Performance Issues

1. **Memory Issues**:
   ```bash
   # Reduce pages for large sites
   --max-pages 50
   ```

2. **Rate Limiting**:
   ```bash
   # Add delays (implemented in scraper)
   # Consider using proxies for high-volume scraping
   ```

3. **Multithreading Performance**:
   ```bash
   # Adjust worker count based on your system
   --max-workers 5    # Conservative for slower systems
   --max-workers 20   # Aggressive for fast systems
   --max-workers 50   # Very aggressive (use with caution)
   ```

## 🏗️ Architecture

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

## 🔧 Development

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
# Manual testing
PYTHONPATH=/home/thari/office/web-scraper python src/cli.py https://httpbin.org --max-pages 1

# API testing
curl http://localhost:8000/health
```

## 📝 Examples

### Complete Workflow

```bash
# 1. Set up environment
source venv/bin/activate
export PYTHONPATH=/home/thari/office/web-scraper

# 2. Scrape a website (with multithreading for speed)
python src/cli.py https://example.com --max-pages 20 --max-workers 15

# 3. Interactive querying
python src/cli.py https://example.com --interactive

# 4. Ask questions
> What products do they sell?
> What are their contact details?
> What are the price ranges?
> Do they have any special offers?
```

### Multithreading Performance Test

```bash
# Test performance with different worker counts
PYTHONPATH=/home/thari/office/web-scraper python test_multithreading.py

# This will test scraping with 1, 5, 10, and 20 workers
# and show the performance improvement
```

### API Workflow

```bash
# 1. Start API server
python -m src.api.main

# 2. Scrape website
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "max_pages": 10}'

# 3. Query the data
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What products are available?"}'
```

## 📄 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📞 Support

For issues and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the API documentation at `/docs`

## 🔄 Updates

### Recent Changes
- **Python 3.12 Support**: Updated dependencies for Python 3.12 compatibility
- **faiss-cpu Fix**: Resolved build issues with newer version
- **Installation Guide**: Enhanced installation instructions
- **Troubleshooting**: Added common issues and solutions

### Version History
- **v1.0.0**: Initial release with basic scraping
- **v1.1.0**: Added RAG capabilities
- **v1.2.0**: Python 3.12 compatibility and improved installation
