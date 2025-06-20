# Webscraper Test Guide

## Overview

This webscraper project implements a modern, high-performance web crawling and semantic search system with the following architecture:

### Core Components

1. **Firecrawl Parser**: Firecrawl (web scraping + markdown + content extraction)
2. **BGE-Large-EN Embeddings**: 1024-dimensional vectors for high-quality semantic search
3. **PostgreSQL + pgvector**: Vector database with HNSW indexing for fast similarity search
4. **Async Crawler**: High-performance crawling with rate limiting and concurrency control

### Technology Stack

- **Web Scraping & Content Processing**: Firecrawl (local server) for robust HTML extraction and markdown generation
- **Embeddings**: BAAI/bge-large-en-v1.5 (1024 dims) via sentence-transformers
- **Database**: PostgreSQL with pgvector extension for vector operations
- **Search**: HNSW index for approximate nearest neighbor search
- **Async Framework**: aiohttp for concurrent HTTP requests

## Setup

### Prerequisites

1. **Firecrawl Server**: Running locally on port 3002
   ```bash
   # Start Firecrawl server (adjust path as needed)
   firecrawl serve --port 3002
   ```

2. **PostgreSQL with pgvector**:
   ```bash
   # Using Docker Compose
   docker-compose up -d
   ```

3. **Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Database Setup

```bash
# Initialize database schema
python -m src.scripts.init_db
```

## Testing Workflow

### 1. Crawl a Website

```bash
# Crawl aezion.com (example domain)
python -m src.crawler.crawler https://aezion.com
```

**Expected Output**:
```
INFO:__main__:Starting crawl from https://aezion.com
INFO:__main__:Max depth: 3
INFO:__main__:Max pages: 1000
EMBD     https://aezion.com
INFO:__main__:Using 0 same-domain links from Firecrawl for https://aezion.com
INFO:__main__:Crawl complete. Total pages processed: 1
```

**What Happens**:
- Firecrawl fetches the page and generates markdown
- Firecrawl extracts clean content and metadata
- Content is stored with markdown checksum for change detection
- Links are extracted and filtered by domain

### 2. Generate Embeddings

```bash
# Generate embeddings for all crawled pages
python -m src.embedder.embedder
```

**Expected Output**:
```
🔍  174 page(s) to embed …
Pages: 100%|██████████| 174/174 [00:44<00:00, 3.93it/s]
✅  Embedding pass complete.
```

**What Happens**:
- BGE-Large-EN model loads (1024 dimensions)
- Content is split into chunks using TextChunker
- Page-level and chunk-level embeddings are generated
- Embeddings are stored in PostgreSQL with pgvector

### 3. Test Semantic Search

```bash
# Search for relevant content
python -m src.search.semantic "custom software development services"
```

**Expected Output**:
```
#1  score=0.713  https://www.aezion.com/blogs/how-to-choose-the-right-custom-software-development-company
How To Choose the Right Custom Software Development Company Choosing a software development company to create a custom solution can be challenging...

#2  score=0.688  https://www.aezion.com/blogs/custom-software-development-project-management
Custom software development and project management can mean the difference between the success and failure of a custom software development project...
```

**What Happens**:
- Query is encoded using BGE-Large-EN model
- HNSW index performs fast similarity search
- Results are ranked by cosine similarity score
- Top-k results are returned with content previews

## Configuration

### Key Settings (src/config/settings.py)

```python
MODEL_CONFIG = {
    "name": "BAAI/bge-large-en-v1.5",  # 1024-dimensional embeddings
    "chunk_tokens": 500,               # Tokens per chunk
}

CRAWLER_CONFIG = {
    "max_depth": 3,                    # Crawl depth limit
    "max_pages": 1000,                 # Page limit
    "crawl_delay": 0.2,                # Seconds between requests
}

SEARCH_CONFIG = {
    "top_k": 5,                        # Number of results
    "ef_search": 200,                  # HNSW search precision
}
```

### Performance Optimizations

- **Rate Limiting**: 0.2s between requests (reduced from 1.0s)
- **Concurrency**: 8 simultaneous requests (handled internally by FirecrawlFetcher)
- **HNSW Index**: Fast approximate nearest neighbor search
- **Bulk Operations**: Efficient database inserts with execute_values

## Database Schema

### Pages Table
```sql
CREATE TABLE pages (
    url TEXT PRIMARY KEY,
    title TEXT,
    clean_text TEXT,                    -- Firecrawl content
    markdown_checksum TEXT,             -- Firecrawl markdown hash
    markdown_changed TIMESTAMP,         -- Change tracking
    metadata JSONB,                     -- Firecrawl metadata
    summary_vec vector(1024),           -- Page-level embedding
    embedded_at TIMESTAMP,              -- Embedding timestamp
    raw_html TEXT                       -- Original HTML
);
```

### Chunks Table
```sql
CREATE TABLE chunks (
    page_url TEXT REFERENCES pages(url),
    chunk_index INTEGER,
    text TEXT,                          -- Chunk content
    vec vector(1024),                   -- Chunk embedding
    PRIMARY KEY (page_url, chunk_index)
);
```

## Troubleshooting

### Common Issues

1. **Firecrawl Connection Error**:
   ```bash
   # Check if Firecrawl is running
   curl http://localhost:3002/health
   ```

2. **Database Connection Error**:
   ```bash
   # Check PostgreSQL status
   docker-compose ps
   ```

3. **Model Loading Error**:
   ```bash
   # Clear model cache
   rm -rf ~/.cache/torch/sentence_transformers/
   ```

4. **Memory Issues**:
   - Reduce `max_depth` or `max_pages` in CRAWLER_CONFIG
   - Reduce `chunk_tokens` in MODEL_CONFIG

### Performance Monitoring

```bash
# Check database size
PGPASSWORD=postgres psql -h localhost -U postgres -d rag -c "SELECT COUNT(*) FROM pages;"
PGPASSWORD=postgres psql -h localhost -U postgres -d rag -c "SELECT COUNT(*) FROM chunks;"

# Check embedding status
PGPASSWORD=postgres psql -h localhost -U postgres -d rag -c "SELECT COUNT(*) FROM pages WHERE embedded_at IS NULL;"
```

## Advanced Testing

### Custom Queries

```bash
# Test different search queries
python -m src.search.semantic "data engineering solutions"
python -m src.search.semantic "cloud computing services"
python -m src.search.semantic "artificial intelligence applications"
```

### Crawl Different Sites

```bash
# Test with different domains
python -m src.crawler.crawler https://example.com
python -m src.crawler.crawler https://docs.python.org
```

### Performance Testing

```bash
# Time the embedding process
time python -m src.embedder.embedder

# Monitor memory usage during crawl
python -m src.crawler.crawler https://aezion.com &
top -p $!
```

## Architecture Benefits

### Firecrawl Parser Advantages
- **Firecrawl**: Robust scraping, high-quality markdown, link extraction, and content extraction
- **Best of Both**: Markdown for display, clean text for embeddings

### BGE-Large-EN Benefits
- **High Quality**: 1024 dimensions vs 768 in previous model
- **Better Performance**: Improved semantic understanding
- **Multilingual**: Supports multiple languages effectively

### Performance Optimizations
- **HNSW Index**: Fast similarity search (O(log n))
- **Concurrent Crawling**: 8x faster than sequential
- **Bulk Operations**: Efficient database writes
- **Change Detection**: Avoids redundant processing

This architecture provides a robust, scalable foundation for web crawling and semantic search with excellent performance characteristics. 