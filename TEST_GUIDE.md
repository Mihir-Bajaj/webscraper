# Webscraper System Test Guide

This guide walks through testing the entire system functionality from database initialization to semantic search.

## Prerequisites

1. Make sure you have Docker installed
2. Make sure you have Python 3.8+ installed
3. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

## Step 1: Start the Database

1. Start the PostgreSQL database with pgvector support:
```bash
docker-compose up -d
```

2. Wait a few seconds for the database to initialize, then verify it's running:
```bash
docker ps
# Should show two containers: rag_db and pg_admin
```

## Step 2: Initialize the Database Schema

1. Install the required Python packages:
```bash
pip install -r requirements.txt
```

2. Initialize the database schema:
```bash
python -m src.scripts.init_db
```

Expected output:
```
✅ Database initialized successfully!
```

## Step 3: Test the Crawler

1. Crawl a test website (using a small, well-structured site):
```bash
python -m src.crawler.crawler https://example.com
```

Expected output:
```
EMBD SEO  https://example.com
```

2. Verify the crawl in the database:
```bash
psql -h localhost -U postgres -d rag -c "SELECT url, title, content_changed FROM pages;"
```

You should see the crawled page with its title and timestamp.

## Step 4: Test the Embedder

1. Run the embedder on the crawled content:
```bash
python -m src.embedder.embedder
```

Expected output:
```
🔍  1 page(s) to embed …
Pages: 100%|███████████████████████████████████████████████████████████████| 1/1 [00:00<00:00, 31068.92it/s]
✅  Embedding pass complete.
```

2. Verify the embeddings in the database:
```bash
psql -h localhost -U postgres -d rag -c "SELECT url, embedded_at FROM pages WHERE summary_vec IS NOT NULL;"
```

You should see the page with its embedding timestamp.

## Step 5: Test Semantic Search

1. Try a semantic search query:
```bash
python -m src.search.semantic "What is this website about?"
```

Expected output:
```
#1  score=0.923  https://example.com
[First 300 characters of the most relevant text chunk...]
```

2. Try another query to test semantic understanding:
```bash
python -m src.search.semantic "Tell me about the main purpose of this site"
```

You should get similar results, showing that the search understands semantic similarity.

## Step 6: Test End-to-End Flow

1. Crawl a more complex site:
```bash
python -m src.crawler.crawler https://python.org
```

2. Run the embedder:
```bash
python -m src.embedder.embedder
```

3. Try multiple semantic queries:
```bash
python -m src.search.semantic "What programming language is this site about?"
python -m src.search.semantic "How can I get started with Python?"
python -m src.search.semantic "What are the main features of Python?"
```

## Troubleshooting

If you encounter any issues:

1. Check database connection:
```bash
psql -h localhost -U postgres -d rag -c "\dt"
```

2. Check if tables are properly created:
```bash
psql -h localhost -U postgres -d rag -c "\d pages"
psql -h localhost -U postgres -d rag -c "\d chunks"
```

3. Check if vector extension is installed:
```bash
psql -h localhost -U postgres -d rag -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

4. Check logs if needed:
```bash
docker logs rag_db
```

## Cleanup

To start fresh:

1. Stop the containers:
```bash
docker-compose down
```

2. Remove the data volume:
```bash
rm -rf pgdata/
```

3. Restart from Step 1

## Expected Results

- Crawler should successfully fetch and parse web pages
- Embedder should create both page-level and chunk-level vectors
- Semantic search should return relevant results even with different phrasings
- The system should handle multiple pages and maintain proper relationships between pages and chunks

## Notes

- The first run of the embedder might take longer as it downloads the MPNet model
- Semantic search results are ranked by similarity score (higher is better)
- The system uses HNSW indexing for fast approximate nearest neighbor search
- All timestamps are stored in UTC 