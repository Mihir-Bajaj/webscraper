"""
Central configuration for the webscraper project.
"""
from typing import Dict, Any

# Database configuration
DB_CONFIG: Dict[str, str] = {
    "dbname": "rag",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
}

# Model configuration
MODEL_CONFIG = {
    "name": "sentence-transformers/all-mpnet-base-v2",
    "dim": 768,
    "chunk_tokens": 500,
}

# Crawler configuration
CRAWLER_CONFIG = {
    "max_depth": 3,
    "max_pages": 1_000,
    "crawl_delay": 1.0,
    "concurrency": 8,
}

# Search configuration
SEARCH_CONFIG = {
    "top_k": 5,
    "ef_search": 200,  # HNSW search parameter
}

# Class imports
from src.core.implementations.aiohttp_fetcher import AiohttpFetcher
from src.core.implementations.readability_parser import ReadabilityParser
from src.core.implementations.postgres_storage import PostgresStorage
from src.core.implementations.mpnet_encoder import MpnetEncoder

FETCHER_CLS = AiohttpFetcher
PARSER_CLS = ReadabilityParser
STORAGE_CLS = PostgresStorage
ENCODER_CLS = MpnetEncoder 