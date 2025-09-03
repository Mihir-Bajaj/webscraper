"""
Central configuration for the webscraper project.
"""
import os
from typing import Dict

# REST API configuration - Updated to use our database API
REST_API_CONFIG = {
    "base_url": os.getenv("REST_CONFIG_BASE_URL", "http://localhost:4000") + "/api",
    "timeout": int(os.getenv("REST_CONFIG_TIMEOUT", "30")),
    "retry_attempts": 3,
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

# Component class names (to avoid circular imports)
FETCHER_CLS_NAME = "src.core.implementations.firecrawl_fetcher.FirecrawlFetcher"
PARSER_CLS_NAME = "src.core.implementations.firecrawl_parser.FirecrawlParser"
STORAGE_CLS_NAME = "src.core.implementations.rest_api_storage.RestApiStorage"