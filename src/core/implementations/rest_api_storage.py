"""
REST API storage implementation for the webscraper project.

This module provides a REST API-based storage backend that:
• Calls REST APIs instead of direct database connections
• Maintains the same interface as PostgresStorage
• Optimizes for bulk operations
• Handles page storage and vector operations separately

Example:
    ```python
    storage = RestApiStorage(rest_config)
    assets = PageAssets(
        url="https://example.com",
        title="Example",
        clean_text="Clean content from Readability",
        seo_head='{"markdown": "# Example", "links": ["https://example.com/about"]}',
        raw_html="<html>...</html>"
    )
    content_changed, _ = storage.upsert_page(assets)
    ```
"""
import requests
import json
from typing import List, Tuple, Optional
from src.core.interfaces.storage import Storage
from src.core.interfaces.parser import PageAssets
from src.config.settings import REST_API_CONFIG

class RestApiStorage(Storage):
    """
    REST API-based storage implementation.
    
    This class implements the Storage interface by making HTTP requests
    to a REST API for all storage operations. It's designed to work
    with our database API.
    
    Attributes:
        base_url: Base URL for the REST API
        timeout: Request timeout in seconds
        retry_attempts: Number of retry attempts for failed requests
        
    Example:
        >>> from src.config.settings import REST_API_CONFIG
        >>> storage = RestApiStorage(REST_API_CONFIG)
        >>> assets = PageAssets(url="https://example.com", ...)
        >>> content_changed, seo_changed = storage.upsert_page(assets)
    """
    
    def __init__(self, rest_cfg: dict):
        """
        Initialize REST API storage with configuration.
        
        Args:
            rest_cfg: Dictionary containing REST API configuration
                - base_url: Base URL for the API
                - timeout: Request timeout in seconds
                - retry_attempts: Number of retry attempts
        """
        self.base_url = rest_cfg["base_url"]
        self.timeout = rest_cfg["timeout"]
        self.retry_attempts = rest_cfg["retry_attempts"]
        self._batch_buffer = []  # Buffer for batching pages
        self._batch_size = 10    # Number of pages to batch together
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

    def _make_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make HTTP request to API"""
        url = f"{self.base_url}/{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=self.timeout)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ DB Error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ DB Request failed: {e}")
            return None

    def _extract_metadata(self, seo_head: str) -> dict:
        """Extract metadata from seo_head JSON string."""
        try:
            if seo_head and seo_head.strip():
                return json.loads(seo_head)
            return {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def _flush_batch(self):
        """Flush the batch buffer to the API"""
        if not self._batch_buffer:
            return
            
        try:
            result = self._make_request("POST", "pages/batch", self._batch_buffer)
            if result is None:
                print(f"❌ DB Failed to store batch of {len(self._batch_buffer)} pages")
                raise Exception("Batch storage failed")
            self._batch_buffer.clear()
        except Exception as e:
            print(f"[ERROR] Exception in _flush_batch: {e}")
            raise

    def flush_all(self):
        """Flush all remaining pages in the batch buffer"""
        if self._batch_buffer:
            self._flush_batch()

    def upsert_page(self, assets: PageAssets) -> tuple[bool, bool]:
        """
        Upsert a page via REST API with batching.
        
        This method:
        1. Extracts metadata from SEO head
        2. Prepares page data for REST API
        3. Adds to batch buffer
        4. Flushes batch when buffer is full
        5. Returns (content_changed, seo_changed) tuple
        
        Args:
            assets: PageAssets object containing page data
            
        Returns:
            Tuple of (content_changed, seo_changed) booleans
            
        Example:
            >>> storage = RestApiStorage(rest_cfg)
            >>> assets = PageAssets(url="https://example.com", ...)
            >>> content_changed, seo_changed = storage.upsert_page(assets)
        """
        try:
            # Extract metadata from SEO head
            metadata = self._extract_metadata(assets.seo_head)
            
            # Add page_type to metadata if not present
            if "page_type" not in metadata:
                metadata["page_type"] = "other"
            
            # Prepare page data for our database API
            from datetime import datetime
            import hashlib
            
            # Create a proper checksum from the clean text (use SHA256 to match firecrawl_parser)
            checksum = hashlib.sha256(assets.clean_text.encode()).hexdigest()
            
            # Get current timestamp for last_seen (always update this)
            current_time = datetime.now().isoformat()
            
            # Check if we need to update markdown_changed by comparing checksums
            # We'll let the API handle this logic since we don't have the previous checksum
            # The API should only update markdown_changed if the checksum changed
            
            page_data = {
                "url": assets.url,
                "title": assets.title,
                "clean_text": assets.clean_text,
                "raw_html": assets.raw_html,
                "markdown_checksum": checksum,
                "markdown_changed": current_time,  # API will handle if this should be updated
                "last_seen": current_time,         # Always update this
                "metadata": metadata,
                "page_type": metadata.get("page_type", "other")
            }
            
            # Add to batch buffer
            self._batch_buffer.append(page_data)
            
            # Flush batch if buffer is full
            if len(self._batch_buffer) >= self._batch_size:
                try:
                    self._flush_batch()
                    return True, False  # content_changed=True, seo_changed=False
                except Exception as e:
                    print(f"❌ DB Failed to store page: {assets.url}")
                    return False, False  # Indicate failure
                
            return True, False  # content_changed=True, seo_changed=False
                
        except Exception as e:
            print(f"❌ DB Failed to prepare page: {assets.url} - {e}")
            return False, False  # Indicate failure

    def pages_for_embedding(self) -> list[tuple[str, str]]:
        """
        Get pages that need embedding via REST API.
        
        This method queries the REST API for pages that have not yet
        been embedded (summary_vec is NULL).
        
        Returns:
            List of (url, clean_text) tuples for pages needing embedding
            
        Example:
            >>> storage = RestApiStorage(rest_cfg)
            >>> pages = storage.pages_for_embedding()
            >>> for url, text in pages:
            ...     print(f"Need to embed: {url}")
        """
        try:
            # Use the pages for embedding endpoint
            response = self._make_request("GET", "pages/for-embedding/list")
            pages_data = response.get("data", {}).get("pages", [])
            
            # Convert to expected format (url, clean_text)
            return [(page["url"], page["clean_text"]) for page in pages_data]
        except Exception as e:
            print(f"[ERROR] Exception in pages_for_embedding: {e}")
            return []

    def save_vectors(self, url: str, vecs: list[list[float]]) -> None:
        """
        Save page and chunk vectors via REST API.
        
        This method:
        1. Computes page vector as mean of chunk vectors
        2. Updates the page's summary vector via REST API
        3. Stores individual chunk vectors via REST API
        
        Args:
            url: The URL of the page
            vecs: List of chunk vectors to store
            
        Example:
            >>> storage = RestApiStorage(rest_cfg)
            >>> # Save vectors for a page with 3 chunks
            >>> vecs = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
            >>> storage.save_vectors("https://example.com", vecs)
        """
        try:
            # Compute page vector as mean of chunk vectors
            import numpy as np
            page_vec = np.mean(vecs, axis=0).tolist()
            
            # Prepare chunks data for our database API
            chunks_data = [
                {
                    "chunk_index": i,
                    "text": f"Chunk {i}",  # Placeholder text
                    "vec": vec.tolist()
                }
                for i, vec in enumerate(vecs)
            ]
            
            # Store chunks using the chunks batch endpoint
            self._make_request("POST", "chunks/batch", {
                "page_url": url,
                "chunks_data": chunks_data
            })
            
            # Update page with summary vector using the vectors embed endpoint
            embed_data = {
                "url": url,
                "page_vector": page_vec,
                "chunks": [
                    {
                        "text": f"Chunk {i}",
                        "vector": vec.tolist()
                    }
                    for i, vec in enumerate(vecs)
                ]
            }
            
            self._make_request("POST", "vectors/embed", embed_data)
            
        except Exception as e:
            print(f"[ERROR] Exception in save_vectors: {e}")
            raise 