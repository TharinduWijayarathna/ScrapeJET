# CURL Commands for RAG System with celltronics.lk

This guide provides curl commands to interact with the RAG system for your scraped celltronics.lk data.

## Prerequisites

1. **Start the API server**:
```bash
cd /home/thari/office/web-scraper
python src/api/main.py
```

2. **Set your OpenAI API key** (if not already set):
```bash
export OPENAI_API_KEY="your-openai-api-key"
```

## 1. Scrape celltronics.lk (if not already done)

```bash
# Scrape the website
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://celltronics.lk",
    "max_pages": 50,
    "max_workers": 5,
    "output_format": "both",
    "llm_provider": "openai",
    "llm_model": "gpt-3.5-turbo"
  }'
```

## 2. Check Available Sites

```bash
# List all available sites
curl -X GET "http://localhost:8000/sites"
```

Expected response:
```json
{
  "sites": ["celltronics.lk"],
  "statistics": {
    "celltronics.lk": {
      "site_name": "celltronics.lk",
      "total_chunks": 150,
      "unique_chunks": 120,
      "duplicate_chunks": 30,
      "deduplication_ratio": 20.0
    }
  }
}
```

## 3. Query celltronics.lk Data

### Query across all sites (including celltronics.lk)
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What products does celltronics.lk sell?",
    "n_results": 5
  }'
```

### Query specifically celltronics.lk
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What products does celltronics.lk sell?",
    "n_results": 5,
    "site_name": "celltronics.lk"
  }'
```

### Alternative: Query using site-specific endpoint
```bash
curl -X POST "http://localhost:8000/query/site/celltronics.lk" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What products does celltronics.lk sell?",
    "n_results": 5
  }'
```

## 4. Common Queries for celltronics.lk

### Product Information
```bash
curl -X POST "http://localhost:8000/query/site/celltronics.lk" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What mobile phones and accessories does celltronics.lk offer?",
    "n_results": 5
  }'
```

### Contact Information
```bash
curl -X POST "http://localhost:8000/query/site/celltronics.lk" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the contact details and address of celltronics.lk?",
    "n_results": 3
  }'
```

### Pricing Information
```bash
curl -X POST "http://localhost:8000/query/site/celltronics.lk" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the prices of mobile phones at celltronics.lk?",
    "n_results": 5
  }'
```

### Services Offered
```bash
curl -X POST "http://localhost:8000/query/site/celltronics.lk" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What services does celltronics.lk provide?",
    "n_results": 3
  }'
```

### Store Locations
```bash
curl -X POST "http://localhost:8000/query/site/celltronics.lk" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Where are the celltronics.lk stores located?",
    "n_results": 3
  }'
```

## 5. Get Site Statistics

```bash
# Get statistics for celltronics.lk
curl -X GET "http://localhost:8000/sites/celltronics.lk/stats"
```

## 6. Clear Site Data (if needed)

```bash
# Clear celltronics.lk data
curl -X DELETE "http://localhost:8000/sites/celltronics.lk"
```

## 7. Check System Status

```bash
# Check if data is loaded
curl -X GET "http://localhost:8000/data/status"

# Health check
curl -X GET "http://localhost:8000/health"
```

## 8. Advanced Queries

### Compare Products
```bash
curl -X POST "http://localhost:8000/query/site/celltronics.lk" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the differences between Samsung and Apple phones at celltronics.lk?",
    "n_results": 7
  }'
```

### Warranty Information
```bash
curl -X POST "http://localhost:8000/query/site/celltronics.lk" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What warranty policies does celltronics.lk offer?",
    "n_results": 3
  }'
```

### Payment Methods
```bash
curl -X POST "http://localhost:8000/query/site/celltronics.lk" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What payment methods does celltronics.lk accept?",
    "n_results": 3
  }'
```

## 9. Batch Queries Script

Create a script to run multiple queries:

```bash
#!/bin/bash

# Array of questions
questions=(
  "What products does celltronics.lk sell?"
  "What are the contact details?"
  "What are the store locations?"
  "What payment methods are accepted?"
  "What warranty policies are offered?"
)

# Loop through questions
for question in "${questions[@]}"; do
  echo "Question: $question"
  echo "Answer:"
  curl -s -X POST "http://localhost:8000/query/site/celltronics.lk" \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"$question\", \"n_results\": 5}" | jq -r '.answer'
  echo "----------------------------------------"
done
```

## 10. Error Handling

### Check if site exists
```bash
# This will return 404 if site doesn't exist
curl -X GET "http://localhost:8000/sites/celltronics.lk/stats"
```

### Handle API errors
```bash
# Check response status
curl -w "\nHTTP Status: %{http_code}\n" -X POST "http://localhost:8000/query/site/celltronics.lk" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What products are available?",
    "n_results": 5
  }'
```

## Expected Response Format

```json
{
  "answer": "Based on the scraped data from celltronics.lk, the store offers a wide range of mobile phones and accessories including...",
  "context": [
    {
      "text": "Product information from celltronics.lk...",
      "metadata": {
        "url": "https://celltronics.lk/products",
        "title": "Products - Celltronics",
        "site_name": "celltronics.lk"
      },
      "distance": 0.123
    }
  ],
  "site_name": "celltronics.lk"
}
```

## Troubleshooting

1. **API not responding**: Make sure the server is running on port 8000
2. **No data found**: Ensure you've scraped celltronics.lk first
3. **Site not found**: Check the exact domain name (celltronics.lk)
4. **Authentication error**: Verify your OpenAI API key is set

## Quick Start Commands

```bash
# 1. Start server
python src/api/main.py &

# 2. Scrape celltronics.lk
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://celltronics.lk", "max_pages": 50}'

# 3. Query the data
curl -X POST "http://localhost:8000/query/site/celltronics.lk" \
  -H "Content-Type: application/json" \
  -d '{"question": "What products does celltronics.lk sell?", "n_results": 5}'
``` 