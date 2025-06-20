# Webscraper - Modern Web Crawling & Semantic Search

A high-performance web crawling and semantic search system that uses Firecrawl for robust scraping and content extraction, powered by BGE-Large-EN embeddings and PostgreSQL with pgvector.

## 🚀 Features

- **Firecrawl Parser**: Firecrawl (scraping + markdown + content extraction)
- **High-Quality Embeddings**: BGE-Large-EN model (1024 dimensions)
- **Vector Search**: PostgreSQL with pgvector and HNSW indexing
- **Async Crawling**: High-performance concurrent web scraping
- **Change Detection**: Intelligent content change tracking
- **Semantic Search**: Natural language query understanding

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Firecrawl     │    │   BGE-Large-EN  │    │   PostgreSQL    │
│   (Scraping &   │───▶│  (Embeddings)   │───▶│   + pgvector    │
│   Extraction)   │    │   1024 dims     │    │   + HNSW Index  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📊 Data Flow Pipeline

### 1. Crawler Execution (`python -m src.crawler.crawler https://aezion.com`)

**Entry Point**: `src/crawler/__main__.py`
- Parses command line arguments
- Initializes crawler with configuration from `src/config/settings.py`
- Starts async crawl process

**Core Crawler**: `src/crawler/crawler.py`
- **`Crawler.crawl()`**: Main orchestration method
  - Initializes BFS frontier with start URL
  - Processes pages level by level (depth 0, 1, 2, etc.)
  - Manages concurrency and rate limiting

**Web Fetching & Content Processing**: `src/core/implementations/firecrawl_fetcher.py` & `src/core/implementations/firecrawl_parser.py`
- **`FirecrawlFetcher.fetch()`**: Sends URL to Firecrawl server
  - POSTs to `http://localhost:3002/v1/scrape`
  - Returns `FetchResult` with HTML, markdown, and links
  - Implements rate limiting (0.2s between requests)
  - Handles 8 concurrent requests via semaphore
- **`FirecrawlParser.parse()`**: Extracts clean text and metadata from Firecrawl output
  - Uses Firecrawl markdown and metadata for all content extraction
  - Returns `PageAssets` object with all extracted data

**Data Storage**: `src/core/implementations/postgres_storage.py`
- **`PostgresStorage.upsert_page()`**: Stores page data
  - Computes markdown checksum from Firecrawl markdown
  - Stores `clean_text`, `raw_html`, `metadata`
  - Tracks changes using `markdown_checksum` and `markdown_changed`
  - Returns change flags for embedding decisions

**Practical Outcome**: 
- Website pages are fetched, parsed, and stored in PostgreSQL
- Each page gets clean content for embeddings and rich markdown for display
- Change detection prevents redundant processing

### 2. Embedder Execution (`python -m src.embedder.embedder`)

**Entry Point**: `src/embedder/embedder.py`
- **`Embedder.run()`**: Main orchestration method
  - Queries database for pages needing embedding
  - Processes pages with progress tracking
  - Generates both page-level and chunk-level embeddings

**Target Selection**: `src/embedder/embedder.py`
- **`Embedder.get_targets()`**: SQL query for pages needing embedding

**Model Loading**: `src/embedder/embedder.py`
- **`SentenceTransformer("BAAI/bge-large-en-v1.5")`**: Loads 1024-dim model
- Downloads model on first run (~1.5GB)
- Caches model for subsequent runs

**Text Chunking**: `src/embedder/chunker.py`
- **`TextChunker.chunk_text()`**: Splits content into chunks
  - Uses sentence boundaries and token limits (see config)
  - Preserves semantic coherence within chunks
  - Returns list of text chunks for embedding

**Embedding Generation**: `src/embedder/embedder.py`
- **`Embedder.embed_page()`**: Creates embeddings for single page
  - **Page-level**: Encodes entire `clean_text` → `summary_vec`
  - **Chunk-level**: Encodes each chunk → `chunks.vec`
  - Uses `normalize_embeddings=True` for cosine similarity
  - Stores 1024-dimensional vectors in PostgreSQL

**Database Storage**: `src/embedder/embedder.py`
- **Page embeddings**: Updates `pages.summary_vec` and `embedded_at`
- **Chunk embeddings**: Bulk insert into `chunks` table
  - Uses `execute_values()` for efficient bulk operations
  - Stores `(page_url, chunk_index, text, vec)` tuples

**Practical Outcome**:
- Clean text content is converted to high-dimensional vectors
- Both page-level and chunk-level embeddings enable flexible search
- Embeddings are optimized for semantic similarity via cosine distance

### 3. Semantic Search Execution (`python -m src.search.semantic "query"`)

**Entry Point**: `src/search/__main__.py`
- Parses command line query
- Initializes search with configuration
- Executes search and formats results

**Search Engine**: `src/search/semantic.py`
- **`SemanticSearch.__init__()`**: Loads BGE-Large-EN model
  - Same model as embedder for consistency
  - Establishes database connection

**Query Processing**: `src/search/semantic.py`
- **`SemanticSearch.search()`**: Main search method
  - Encodes query using same BGE-Large-EN model
  - Normalizes query vector for cosine similarity
  - Sets HNSW search parameters (`ef_search`)

**Vector Search**: `src/search/semantic.py`
- **SQL Query**: Performs similarity search using pgvector
- **HNSW Index**: Fast approximate nearest neighbor search
- **Cosine Distance**: `<=>` operator computes 1 - cosine_similarity
- **Score Range**: 0.0 (dissimilar) to 1.0 (identical)

**Result Formatting**: `src/search/semantic.py`
- **`SemanticSearch.format_results()`**: Formats search results
  - Ranks results by similarity score
  - Shows URL, score, and content preview (300 chars)
  - Returns formatted string for display

**Practical Outcome**:
- Natural language queries find semantically similar content
- Results ranked by relevance score (higher = more relevant)
- Content previews help users understand match quality
- Fast response times via HNSW indexing

## 🛠️ Technology Stack

- **Web Scraping**: Firecrawl (local server)
- **Content Processing**: Firecrawl
- **Embeddings**: BAAI/bge-large-en-v1.5
- **Database**: PostgreSQL + pgvector
- **Search**: HNSW approximate nearest neighbor
- **Async Framework**: aiohttp

## 📦 Installation

### Prerequisites

1. **Firecrawl Server** (running on port 3002):
   ```bash
   firecrawl serve --port 3002
   ```

2. **PostgreSQL with pgvector**:
   ```bash
   docker-compose up -d
   ```

3. **Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Database Setup

```bash
python -m src.scripts.init_db
```

## 🚀 Quick Start

### 1. Crawl a Website

```bash
python -m src.crawler.crawler https://aezion.com
```

### 2. Generate Embeddings

```bash
python -m src.embedder.embedder
```

### 3. Search Content

```bash
python -m src.search.semantic "custom software development services"
```

## 📊 Performance

- **Crawling**: 8 concurrent requests, 0.2s rate limit
- **Embeddings**: 1024-dimensional vectors
- **Search**: HNSW index for O(log n) similarity search
- **Storage**: Efficient bulk operations with pgvector

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