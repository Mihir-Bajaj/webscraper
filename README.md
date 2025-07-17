# Webscraper - Modern Web Crawling & Semantic Search

A high-performance web crawling and semantic search system that uses Firecrawl for robust scraping and content extraction, powered by BGE-Large-EN embeddings and PostgreSQL with pgvector.

## 🚀 Features

- **Firecrawl Parser**: Firecrawl (scraping + markdown + content extraction)
- **High-Quality Embeddings**: BGE-Large-EN model (1024 dimensions)
- **Vector Search**: PostgreSQL with pgvector and HNSW indexing
- **Async Crawling**: High-performance concurrent web scraping
- **Change Detection**: Intelligent content change tracking
- **Semantic Search**: Natural language query understanding
- **Smart Domain Matching**: Handles www/non-www domain variations
- **URL Validation**: Filters out non-crawlable URLs (javascript:, tel:, etc.)

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Firecrawl     │    │   BGE-Large-EN  │    │   PostgreSQL    │
│   (Scraping &   │───▶│  (Embeddings)   │───▶│   + pgvector    │
│   Extraction)   │    │   1024 dims     │    │   + HNSW Index  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📦 Installation & Setup

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

### Step 5: Initialize Database

```bash
# Initialize the database schema
python db_utils.py init

# Check database status
python db_utils.py status
```

### Step 6: Test the Setup

Run the comprehensive test suite:

```bash
python test_system.py
```

Expected output:
```
🚀 Starting comprehensive system test...

🔍 Testing Firecrawl API...
✅ Firecrawl API working correctly

🗄️  Testing database connection...
✅ Database connection successful

📊 Testing metadata storage...
✅ Full Firecrawl response found in metadata

🔍 Testing search functionality...
✅ Search functionality working

📊 Test Results:
==================================================
   Firecrawl API: ✅ PASS
   Database Connection: ✅ PASS
   Metadata Storage: ✅ PASS
   Search Functionality: ✅ PASS

🎉 All tests passed!
✅ System is ready for use!
```

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

## 🚀 Quick Start

### 1. Test the Setup

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

### 2. Crawl a Website

```bash
python -m src.crawler.crawler https://aezion.com
```

**Expected Output**: The crawler should process multiple pages (not just 1):
```
INFO: Starting crawl from https://aezion.com
INFO: Processing 1 URLs at depth 0
INFO: Using 28 same-domain links from Firecrawl for https://www.aezion.com (filtered from 32 total)
INFO: Added 27 new URLs to frontier from https://www.aezion.com
...
INFO: Crawl complete. Total pages processed: 174
```

### 3. Generate Embeddings

```bash
python -m src.embedder.embedder
```

### 4. Search Content

```bash
python -m src.search.semantic "custom software development services"
```

## 🗄️ Database

### Schema

The system uses PostgreSQL with pgvector for vector operations:

```sql
-- Main pages table
CREATE TABLE pages (
    url                 text PRIMARY KEY,           -- Unique URL identifier
    title               text,                       -- Page title from HTML
    clean_text          text,                       -- Cleaned content from Firecrawl
    raw_html            text,                       -- Original HTML content
    markdown_checksum   text,                       -- SHA256 hash of markdown content
    markdown_changed    timestamptz,                -- When content last changed
    metadata            jsonb,                      -- Complete Firecrawl response data
    last_seen           timestamptz,                -- Last crawl timestamp
    summary_vec         vector(1024),               -- Page-level embedding
    embedded_at         timestamptz,                -- When embedding was created
    category            varchar(20),                -- Page category (content, hubs, etc.)
    category_confidence decimal(3,2)                -- Confidence in categorization
);

-- Text chunks for granular search
CREATE TABLE chunks (
    page_url    text REFERENCES pages(url) ON DELETE CASCADE,
    chunk_index integer,
    text        text,
    vec         vector(1024),
    PRIMARY KEY (page_url, chunk_index)
);

-- Keywords with embeddings
CREATE TABLE keywords (
    url         text REFERENCES pages(url) ON DELETE CASCADE,
    phrase      text NOT NULL,
    embedding   vector(1024)
);
```

### Database Utilities

Use `db_utils.py` for database operations:

```bash
# Check database status and statistics
python db_utils.py status

# Check metadata structure
python db_utils.py metadata

# Initialize database schema
python db_utils.py init

# Run all database checks
python db_utils.py all
```

### pgAdmin Access

Access pgAdmin at http://localhost:5050:
- **Email**: admin@example.com
- **Password**: admin

**Connection Details:**
- **Host**: rag_db
- **Port**: 5432
- **Database**: rag
- **Username**: postgres
- **Password**: postgres

## 🔧 Configuration

Key settings in `src/config/settings.py`:

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

## 🛠️ Troubleshooting

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

## 📊 Performance

- **Crawling**: 8 concurrent requests, 0.2s rate limit
- **Embeddings**: 1024-dimensional vectors
- **Search**: HNSW index for O(log n) similarity search
- **Storage**: Efficient bulk operations with pgvector

## 📚 Documentation

- [Test Guide](TEST_GUIDE.md) - Comprehensive testing instructions
- [Architecture Details](TEST_GUIDE.md#architecture-benefits) - Technical deep dive
- [Troubleshooting](TEST_GUIDE.md#troubleshooting) - Common issues and solutions

## 🎯 Use Cases

- **Content Discovery**: Crawl and index website content
- **Semantic Search**: Find relevant content using natural language
- **Change Monitoring**: Track content updates across websites
- **Knowledge Base**: Build searchable document collections

## 🔍 Example Output

```bash
$ python -m src.search.semantic "custom software development services"

#1  score=0.713  https://www.aezion.com/blogs/how-to-choose-the-right-custom-software-development-company
How To Choose the Right Custom Software Development Company Choosing a software development company to create a custom solution can be challenging...

#2  score=0.688  https://www.aezion.com/blogs/custom-software-development-project-management
Custom software development and project management can mean the difference between the success and failure of a custom software development project...
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details. 