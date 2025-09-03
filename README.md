# Webscraper - Modern Web Crawling & Semantic Search

A high-performance web crawling and semantic search system that uses Firecrawl for robust scraping and content extraction, powered by BGE-Large-EN embeddings and external database API.

## 🚀 Features

- **Firecrawl Parser**: Firecrawl (scraping + markdown + content extraction)
- **High-Quality Embeddings**: BGE-Large-EN model (1024 dimensions)
- **Vector Search**: External database API with pgvector support
- **Async Crawling**: High-performance concurrent web scraping
- **Change Detection**: Intelligent content change tracking
- **Semantic Search**: Natural language query understanding
- **Smart Domain Matching**: Handles www/non-www domain variations
- **URL Validation**: Filters out non-crawlable URLs (javascript:, tel:, etc.)

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Firecrawl     │    │   BGE-Large-EN  │    │   External      │
│   (Scraping &   │───▶│  (Embeddings)   │───▶│   Database API  │
│   Extraction)   │    │   1024 dims     │    │   + pgvector    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📦 Installation & Setup

### Prerequisites

1. **Docker and Docker Compose** (for Firecrawl)
2. **Python 3.8+** with virtual environment support
3. **Git** for cloning the repository
4. **External Database API** running on `localhost:4000`

### Step 1: Clone and Setup Python Environment

```bash
git clone <repository-url>
cd webscraper
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Start Firecrawl Service

**Start Firecrawl Server:**
```bash
# Navigate to the crawler directory (adjust path as needed)
cd ../crawler/firecrawl
docker-compose up -d

# Verify Firecrawl containers are running
docker ps --filter "name=firecrawl"
# Should show: firecrawl-api-1, firecrawl-playwright-service-1, firecrawl-redis-1, firecrawl-worker-1
```

### Step 3: Start Webscraper API

**Start the Webscraper API:**
```bash
# Return to webscraper directory
cd ../../webscraper

# Start the webscraper API
docker-compose -f api/host/docker-compose.yml up -d

# Verify webscraper API is running
docker ps --filter "name=webscraper"
# Should show: webscraper-api (port 8000)
```

### Step 4: Verify Services Are Running

```bash
# Check all containers
docker ps

# Expected output should show:
# - firecrawl-api-1 (port 3002)
# - firecrawl-playwright-service-1
# - firecrawl-redis-1
# - firecrawl-worker-1
# - webscraper-api (port 8000)

# Test Firecrawl API
curl -X POST http://localhost:3002/v1/scrape \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","formats":["html","markdown","links"]}'

# Test Webscraper API
curl http://localhost:8000/
```

## 🚀 Quick Start

### 1. Test the Setup

Run the integration test to verify everything is working:

```bash
python test_firecrawl_integration.py
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

### 2. Start Crawling

```bash
# Start a crawl job
curl -X POST http://localhost:8000/api/crawl \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","max_depth":2,"max_pages":10}'

# Check job status
curl http://localhost:8000/api/crawl/{job_id}/status

# Search crawled content
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query":"your search query","limit":5}'
```

## 🛠️ Docker Management Commands

### Start Services
```bash
# Start Firecrawl
cd ../crawler/firecrawl && docker-compose up -d

# Start Webscraper API
cd ../../webscraper && docker-compose -f api/host/docker-compose.yml up -d
```

### Stop Services
```bash
# Stop Firecrawl
cd ../crawler/firecrawl && docker-compose down

# Stop Webscraper API
cd ../../webscraper && docker-compose -f api/host/docker-compose.yml down
```

### Check Service Status
```bash
# Check running containers
docker ps

# Check Firecrawl logs
cd ../crawler/firecrawl && docker-compose logs -f api

# Check Webscraper API logs
cd ../../webscraper && docker-compose -f api/host/docker-compose.yml logs -f
```

### Restart Services
```bash
# Restart Firecrawl
cd ../crawler/firecrawl && docker-compose restart

# Restart Webscraper API
cd ../../webscraper && docker-compose -f api/host/docker-compose.yml restart
```

## 🔧 Configuration

Key settings in `src/config/settings.py`:

```python
# REST API configuration - Points to external database API
REST_API_CONFIG = {
    "base_url": "http://localhost:4000/api",
    "timeout": 30,
    "retry_attempts": 3,
}

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

#### 2. "Connection refused" to Database API
**Error**: `Cannot connect to host localhost:4000`
**Solution**: Start the external database API service

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

# Test Webscraper API
curl http://localhost:8000/

# Test Database API
curl http://localhost:4000/health
```

## 📊 Performance

- **Crawling**: 8 concurrent requests, 0.2s rate limit
- **Embeddings**: 1024-dimensional vectors
- **Search**: HNSW index for O(log n) similarity search
- **Storage**: External database API with efficient bulk operations

## 📚 API Documentation

### Webscraper API Endpoints

- **Health Check**: `GET /`
- **Start Crawl**: `POST /api/crawl`
- **Crawl Status**: `GET /api/crawl/{job_id}/status`
- **Search**: `POST /api/search`

### Example Usage

```bash
# Start a crawl
curl -X POST http://localhost:8000/api/crawl \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","max_depth":2,"max_pages":10}'

# Search content
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query":"machine learning","limit":5}'
```

## 📚 Documentation

- [Test Guide](TEST_GUIDE.md) - Comprehensive testing instructions
- [Architecture Details](TEST_GUIDE.md#architecture-benefits) - Technical deep dive 