# Site-Wise RAG System

This update enhances the web scraper with RAG (Retrieval-Augmented Generation) to support site-wise organization of scraped data. Now you can scrape multiple websites and query them individually or across all sites.

## Key Features

### 🏗️ Site-Wise Organization
- **Automatic Site Detection**: Documents are automatically organized by domain/site
- **Separate Collections**: Each site gets its own vector store collection
- **Site-Specific Queries**: Query individual sites or across all sites
- **Deduplication Per Site**: Prevents duplicate content within each site

### 🔍 Enhanced Querying
- **Site-Specific Search**: Query within a specific website's data
- **Cross-Site Search**: Query across all scraped websites
- **Site Statistics**: View detailed statistics for each site
- **Interactive Mode**: Switch between sites during interactive sessions

### 📊 Management Features
- **Site Listing**: View all available sites
- **Site Statistics**: Get detailed stats for each site
- **Site Clearing**: Remove specific sites from the vector store
- **Content Deduplication**: Automatic removal of duplicate content per site

## Usage Examples

### 1. Scrape Multiple Sites

```bash
# Scrape first site
python src/cli.py --url https://example.com --max-pages 10

# Scrape second site (data will be organized by site)
python src/cli.py --url https://demo.testfire.net --max-pages 10

# Scrape third site
python src/cli.py --url https://httpbin.org --max-pages 5
```

### 2. List Available Sites

```bash
python src/cli.py --list-sites
```

### 3. Query Specific Site

```bash
# Query a specific site
python src/cli.py --query "What products are available?" --site example.com

# Query across all sites
python src/cli.py --query "What products are available?"
```

### 4. Interactive Mode

```bash
python src/cli.py --interactive
```

In interactive mode, you can use these commands:
- `sites` - List available sites
- `stats` - Show site statistics
- `site <site_name>` - Switch to querying a specific site
- `all` - Switch to querying across all sites

### 5. Clear Specific Site

```bash
python src/cli.py --clear-site example.com
```

## API Usage

### Initialize RAG System

```python
from src.rag.vector_store import VectorStore
from src.rag.llm_interface import OpenAIInterface, RAGSystem

# Initialize
vector_store = VectorStore()
llm_interface = OpenAIInterface()
rag_system = RAGSystem(vector_store, llm_interface)
```

### Add Documents (Auto-organized by site)

```python
# Documents will be automatically organized by site based on URL
rag_system.add_documents(scraped_data)
```

### Query Specific Site

```python
# Query a specific site
answer = rag_system.query_site_specific("What products are available?", "example.com")

# Query across all sites
answer = rag_system.query("What products are available?")
```

### Get Site Information

```python
# List all sites
sites = rag_system.get_sites()

# Get statistics for a specific site
stats = rag_system.get_site_stats("example.com")

# Get statistics for all sites
all_stats = rag_system.get_all_sites_stats()
```

## Example Script

Run the example script to see the site-wise RAG in action:

```bash
# Demo mode
python example_site_wise_rag.py

# Interactive demo
python example_site_wise_rag.py interactive
```

## Technical Details

### Vector Store Organization

- **Collection Naming**: Sites are stored as `site_<domain>` collections
- **Domain Extraction**: Automatically extracts domain from URLs
- **Content Hashing**: Each site maintains its own content hash set for deduplication
- **Metadata Enrichment**: All chunks include site information in metadata

### Search Capabilities

- **Site-Specific Search**: Queries only the specified site's collection
- **Cross-Site Search**: Queries all collections and merges results
- **Distance-Based Ranking**: Results are ranked by similarity across all sites
- **Site Attribution**: Results include site information for context

### Performance Benefits

- **Faster Site-Specific Queries**: Only searches relevant site data
- **Better Context**: Site-specific queries provide more focused results
- **Scalability**: Each site's data is isolated, improving performance
- **Memory Efficiency**: Separate collections reduce memory usage

## Migration from Previous Version

The new system is backward compatible. Existing data will be automatically migrated:

1. **Existing Data**: Will be moved to a default collection
2. **New Scrapes**: Will be automatically organized by site
3. **Mixed Queries**: Can query both old and new data

## Configuration

### Environment Variables

```bash
# Required for OpenAI
export OPENAI_API_KEY="your-api-key"

# Optional for AWS Bedrock
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
```

### Vector Store Location

By default, vector stores are stored in `data/vectorstore/`. You can customize this:

```python
vector_store = VectorStore(persist_directory="custom/path")
```

## Troubleshooting

### Common Issues

1. **No sites found**: Make sure you've scraped some websites first
2. **Site not found**: Check the exact domain name (without www)
3. **Permission errors**: Vector store will fall back to `/tmp/vectorstore`

### Debug Mode

Enable debug logging:

```bash
python src/cli.py --log-level DEBUG --interactive
```

## Future Enhancements

- **Site Groups**: Group related sites together
- **Cross-Site Analytics**: Compare data across sites
- **Site Templates**: Predefined scraping templates for common site types
- **Incremental Updates**: Update specific sites without re-scraping everything 