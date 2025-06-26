# Webscraper Test Guide

## Overview

This webscraper project implements a modern, high-performance web crawling and semantic search system with the following architecture:

### Core Components

1. **Firecrawl Parser**: Firecrawl (web scraping + markdown + content extraction)
2. **BGE-Large-EN Embeddings**: 1024-dimensional vectors for high-quality semantic search
3. **PostgreSQL + pgvector**: Vector database with HNSW indexing for fast similarity search
4. **Async Crawler**: High-performance crawling with rate limiting and concurrency control
5. **Smart Domain Matching**: Handles www/non-www domain variations automatically
6. **URL Validation**: Filters out non-crawlable URLs (javascript:, tel:, mailto:, etc.)

### Technology Stack

- **Web Scraping & Content Processing**: Firecrawl (local server) for robust HTML extraction and markdown generation
- **Embeddings**: BAAI/bge-large-en-v1.5 (1024 dims) via sentence-transformers
- **Database**: PostgreSQL with pgvector extension for vector operations
- **Search**: HNSW index for approximate nearest neighbor search
- **Async Framework**: aiohttp for concurrent HTTP requests

## Setup

### Prerequisites

1. **Docker and Docker Compose** (for database and Firecrawl)
2. **Python 3.8+** with virtual environment support
3. **Git** for cloning the repository

### Step 1: Clone and Setup Python Environment

```bash
git clone <repository-url>
cd webscraper
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Start All Services with Docker

#### Option A: Start Services Individually

**Start Firecrawl Server:**
```bash
# Navigate to the crawler directory (adjust path as needed)
cd ../crawler/firecrawl
docker-compose up -d

# Verify Firecrawl containers are running
docker ps --filter "name=firecrawl"
# Should show: firecrawl-api-1, firecrawl-playwright-service-1, firecrawl-redis-1, firecrawl-worker-1
```

**Start PostgreSQL Database:**
```bash
# Return to webscraper directory
cd ../../webscraper

# Start the database
docker-compose up -d db

# Verify database is running
docker ps --filter "name=rag_db"
# Should show: rag_db (PostgreSQL with pgvector)
```

#### Option B: Start All Services at Once

Create a convenience script to start everything:

```bash
# Create a start-services.sh script
cat > start-services.sh << 'EOF'
#!/bin/bash
echo "🚀 Starting all webscraper services..."

# Start Firecrawl
echo "📡 Starting Firecrawl..."
cd ../crawler/firecrawl
docker-compose up -d

# Start PostgreSQL
echo "🗄️  Starting PostgreSQL..."
cd ../../webscraper
docker-compose up -d db

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check status
echo "📊 Service Status:"
docker ps --filter "name=firecrawl" --filter "name=rag_db"

echo "✅ All services started!"
echo "🌐 Firecrawl API: http://localhost:3002"
echo "🗄️  PostgreSQL: localhost:5432"
EOF

chmod +x start-services.sh
./start-services.sh
```

#### Option C: Using Docker Compose Override (Advanced)

Create a `docker-compose.override.yml` to start both services from the webscraper directory:

```bash
# Create docker-compose.override.yml
cat > docker-compose.override.yml << 'EOF'
version: "3.9"
services:
  firecrawl-api:
    image: ghcr.io/mendableai/firecrawl:latest
    ports:
      - "3002:3002"
    environment:
      - REDIS_URL=redis://firecrawl-redis:6379
      - PLAYWRIGHT_MICROSERVICE_URL=http://firecrawl-playwright:3000/scrape
    depends_on:
      - firecrawl-redis
      - firecrawl-playwright

  firecrawl-playwright:
    image: ghcr.io/mendableai/playwright-service:latest
    environment:
      - PORT=3000

  firecrawl-redis:
    image: redis:alpine
    command: redis-server --bind 0.0.0.0

  firecrawl-worker:
    image: ghcr.io/mendableai/firecrawl:latest
    environment:
      - REDIS_URL=redis://firecrawl-redis:6379
      - PLAYWRIGHT_MICROSERVICE_URL=http://firecrawl-playwright:3000/scrape
    depends_on:
      - firecrawl-redis
      - firecrawl-playwright
    command: ["pnpm", "run", "workers"]
EOF

# Start everything with one command
docker-compose up -d
```

### Step 3: Verify Services Are Running

```bash
# Check all containers
docker ps

# Expected output should show:
# - firecrawl-api-1 (port 3002)
# - firecrawl-playwright-service-1
# - firecrawl-redis-1
# - firecrawl-worker-1
# - rag_db (port 5432)

# Test Firecrawl API
curl -X POST http://localhost:3002/v1/scrape \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","formats":["html","markdown","links"]}'

# Test database connection
python -c "import psycopg2; conn = psycopg2.connect(dbname='rag', user='postgres', password='postgres', host='localhost'); print('✅ Database connected!')"
```

### Step 4: Initialize Database

```bash
python -m src.scripts.init_db
```

### Step 5: Test the Setup

Run the integration test to verify everything is working:

```bash
python test_firecrawl_integration.py
```

Expected output:
```
🚀 Starting Firecrawl integration tests...

Testing Firecrawl API directly...
POSTing to http://localhost:3002/v1/scrape...
✅ Scrape completed successfully!

==================================================
Testing FirecrawlFetcher integration...
✅ Crawl completed successfully!

🎉 All tests passed! Firecrawl integration is working correctly.
```

## 🛠️ Docker Management Commands

### Start Services
```bash
# Start Firecrawl
cd ../crawler/firecrawl && docker-compose up -d

# Start PostgreSQL
cd ../../webscraper && docker-compose up -d db

# Or use the convenience script
./start-services.sh
```

### Stop Services
```bash
# Stop Firecrawl
cd ../crawler/firecrawl && docker-compose down

# Stop PostgreSQL
cd ../../webscraper && docker-compose down

# Stop all services
docker-compose down
```

### Check Service Status
```bash
# Check running containers
docker ps

# Check Firecrawl logs
cd ../crawler/firecrawl && docker-compose logs -f api

# Check database logs
docker-compose logs -f db
```

### Restart Services
```bash
# Restart Firecrawl
cd ../crawler/firecrawl && docker-compose restart

# Restart PostgreSQL
cd ../../webscraper && docker-compose restart db

# Restart everything
./start-services.sh
```

### Clean Up (if needed)
```bash
# Stop and remove all containers
docker-compose down

# Remove volumes (WARNING: This will delete all data)
docker-compose down -v

# Remove all unused containers, networks, and images
docker system prune -a
```

## Testing Workflow

### 1. Crawl a Website

```bash
# Crawl aezion.com (example domain)
python -m src.crawler.crawler https://aezion.com
```

**Expected Output** (should process multiple pages, not just 1):
```
INFO:__main__:Starting crawl from https://aezion.com
INFO:__main__:Max depth: 3
INFO:__main__:Max pages: 1000
INFO:__main__:Processing 1 URLs at depth 0
INFO:__main__:Using 28 same-domain links from Firecrawl for https://www.aezion.com (filtered from 32 total)
INFO:__main__:Added 27 new URLs to frontier from https://www.aezion.com
...
INFO:__main__:Crawl complete. Total pages processed: 174
```

**What Happens**:
- Firecrawl fetches the page and generates markdown
- Firecrawl extracts clean content and metadata
- Firecrawl provides a list of links (not parsed from HTML)
- Links are filtered for same-domain and crawlable URLs
- Content is stored with markdown checksum for change detection

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

#### 1. "Connection refused" to Firecrawl API
**Error**: `Cannot connect to host localhost:3002`
**Solution**: 
```bash
cd ../crawler/firecrawl
docker-compose up -d
```

#### 2. "Connection refused" to PostgreSQL
**Error**: `connection to server at "localhost" (::1), port 5432 failed`
**Solution**:
```bash
docker-compose up -d db
```

#### 3. Only 1 page crawled instead of many
**Issue**: Crawler only processes homepage
**Cause**: Domain matching issue (aezion.com vs www.aezion.com)
**Status**: ✅ **Fixed** - The crawler now handles www/non-www variations automatically

#### 4. "Invalid string" errors from Firecrawl API
**Error**: `Firecrawl API error 400 for javascript:void(0): {"error":"Bad Request","details":[{"code":"invalid_string"}]}`
**Cause**: Non-HTTP(S) URLs being sent to Firecrawl
**Status**: ✅ **Fixed** - The crawler now filters out javascript:, tel:, mailto: links before sending to Firecrawl

#### 5. ModuleNotFoundError for aiohttp
**Error**: `ModuleNotFoundError: No module named 'aiohttp'`
**Solution**:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

#### 6. Firecrawl Connection Error (Legacy)
```bash
# Check if Firecrawl is running
curl http://localhost:3002/health
```

#### 7. Database Connection Error (Legacy)
```bash
# Check PostgreSQL status
docker-compose ps
```

#### 8. Model Loading Error
```bash
# Clear model cache
rm -rf ~/.cache/torch/sentence_transformers/
```

#### 9. Memory Issues
- Reduce `max_depth` or `max_pages` in CRAWLER_CONFIG
- Reduce `chunk_tokens` in MODEL_CONFIG

### Verification Commands

Check if services are running:
```bash
# Check Docker containers
docker ps

# Test Firecrawl API directly
curl -X POST http://localhost:3002/v1/scrape \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","formats":["html","markdown","links"]}'

# Test database connection
python -c "import psycopg2; conn = psycopg2.connect(dbname='rag', user='postgres', password='postgres', host='localhost'); print('Database connected!')"
```

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
- **Robust Scraping**: Handles JavaScript, dynamic content, and complex layouts
- **High-Quality Markdown**: Clean, structured content extraction
- **Link Extraction**: Pre-processed links from Firecrawl (not raw HTML parsing)
- **Metadata**: Rich metadata extraction (title, description, etc.)

### Smart Domain Matching
- **www/non-www Handling**: Treats `aezion.com` and `www.aezion.com` as the same domain
- **URL Validation**: Filters out non-crawlable URLs before sending to Firecrawl
- **Error Prevention**: Prevents "invalid_string" errors from non-HTTP(S) URLs

### BGE-Large-EN Benefits
- **High Quality**: 1024 dimensions vs 768 in previous model
- **Better Performance**: Improved semantic understanding
- **Multilingual**: Supports multiple languages effectively

This architecture provides a robust, scalable foundation for web crawling and semantic search with excellent performance characteristics. 