"""
Central configuration for the webscraper project.
"""
from typing import Dict

# Database configuration
DB_CONFIG: Dict[str, str] = {
    "dbname": "rag",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
}

# Model configuration
MODEL_CONFIG = {
    "name": "BAAI/bge-large-en-v1.5",
    "chunk_tokens": 500,
}

# Crawler configuration
CRAWLER_CONFIG = {
    "max_depth": 3,
    "max_pages": 1_000,
    "crawl_delay": 0.2,
}

# Search configuration
SEARCH_CONFIG = {
    "top_k": 5,
    "ef_search": 200,  # HNSW search parameter
}

# Class imports
from src.core.implementations.firecrawl_fetcher import FirecrawlFetcher
from src.core.implementations.firecrawl_parser import FirecrawlParser
from src.core.implementations.postgres_storage import PostgresStorage

# Component classes
FETCHER_CLS = FirecrawlFetcher
PARSER_CLS = FirecrawlParser
STORAGE_CLS = PostgresStorage