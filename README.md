# Webscraper with Semantic Search

A Python project for crawling websites, embedding their content, and performing semantic search.

## Project Structure

```
src/
├── config/          # Configuration settings
├── core/           # Core interfaces and implementations
│   ├── interfaces/    # Protocol definitions
│   ├── implementations/  # Concrete implementations
│   └── checksum.py      # Content hashing utilities
├── crawler/        # Web crawler functionality
├── embedder/       # Text embedding functionality
├── search/         # Semantic search functionality
└── scripts/        # Utility scripts
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Initialize the database:
```bash
python -m src.scripts.init_db
```

## Usage

1. Crawl a website:
```bash
python -m src.crawler.crawler https://example.com
```

2. Embed the crawled pages:
```bash
python -m src.embedder.embedder
```

3. Search the content:
```bash
python -m src.search.semantic "your question here"
```

## Components

- **Crawler**: Concurrent BFS crawler that extracts content from websites
- **Embedder**: Converts text into vector embeddings using MPNet
- **Search**: Performs semantic search using vector similarity
- **Storage**: PostgreSQL-based storage with vector support

## Configuration

All configuration is centralized in `src/config/settings.py`:
- Database settings
- Model parameters
- Crawler settings
- Search parameters 