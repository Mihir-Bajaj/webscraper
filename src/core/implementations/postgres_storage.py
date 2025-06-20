"""
PostgreSQL storage implementation for the webscraper project.

This module provides a PostgreSQL-based storage backend that:
• Stores page content, metadata, and embeddings
• Tracks content changes using markdown checksums
• Supports vector similarity search with pgvector
• Manages hybrid Firecrawl + Readability data

Database schema:
- pages: Main page data with clean_text (Readability) and metadata (Firecrawl)
- chunks: Text chunks with vector embeddings for semantic search
- Uses markdown_checksum for change detection (from Firecrawl markdown)
- Stores metadata as JSONB for flexible querying

Example:
    ```python
    storage = PostgresStorage(db_config)
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
import psycopg2
import hashlib
import json
from src.core.interfaces.storage import Storage
from src.core.interfaces.parser import PageAssets

class PostgresStorage(Storage):
    """
    PostgreSQL-based storage implementation.
    
    This implementation uses PostgreSQL to store:
    1. Page content and metadata
    2. Markdown checksums (from Firecrawl)
    3. Change timestamps
    4. Page and chunk embeddings
    
    The storage tracks changes in markdown content,
    making it easy to identify which pages need re-embedding.
    
    Attributes:
        conn: PostgreSQL connection
        cur: Database cursor
        
    Example:
        ```python
        # Initialize storage
        storage = PostgresStorage({
            "dbname": "webscraper",
            "user": "postgres",
            "password": "secret"
        })
        
        # Store page data
        assets = PageAssets(
            url="https://example.com",
            title="Example",
            clean_text="Content",
            seo_head="<head>...</head>",
            raw_html="<html>...</html>"
        )
        content_changed, _ = storage.upsert_page(assets)
        ```
    """
    
    def __init__(self, db_cfg):
        """
        Initialize PostgreSQL storage.
        
        Args:
            db_cfg: Dictionary of PostgreSQL connection parameters
            
        Example:
            >>> storage = PostgresStorage({
            ...     "dbname": "webscraper",
            ...     "user": "postgres"
            ... })
            >>> storage.conn is not None
            True
        """
        self.conn = psycopg2.connect(**db_cfg)
        self.conn.autocommit = True
        self.cur  = self.conn.cursor()

    def _compute_markdown_checksum(self, markdown_content: str) -> str:
        """Compute SHA256 hash of markdown content."""
        return hashlib.sha256(markdown_content.encode('utf-8')).hexdigest()

    def _extract_metadata(self, seo_head: str) -> dict:
        """Extract metadata from seo_head JSON string."""
        try:
            if seo_head and seo_head.strip():
                return json.loads(seo_head)
            return {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def upsert_page(self, assets: PageAssets) -> tuple[bool, bool]:
        """
        Store or update page data.
        
        This method:
        1. Computes markdown checksum from clean_text (Firecrawl markdown)
        2. Extracts metadata from seo_head
        3. Inserts new pages if they don't exist
        4. Updates existing pages and tracks changes
        5. Returns change flags (content_changed, _) - second value is always False now
        
        Args:
            assets: The page assets to store or update
            
        Returns:
            Tuple of (content_changed, _) where:
            - content_changed: True if the page content has changed
            - _: Always False (kept for interface compatibility)
            
        Example:
            >>> storage = PostgresStorage(db_cfg)
            >>> assets = PageAssets(
            ...     url="https://example.com",
            ...     title="Example",
            ...     clean_text="# Example\n\nContent from Firecrawl",
            ...     seo_head='{"links": ["https://example.com/about"], "source": "firecrawl"}',
            ...     raw_html="<html>...</html>"
            ... )
            >>> content_changed, _ = storage.upsert_page(assets)
            >>> content_changed  # True for new pages
            True
        """
        try:
            # Compute markdown checksum from clean_text (Firecrawl markdown)
            markdown_cs = self._compute_markdown_checksum(assets.clean_text)
            
            # Extract metadata from seo_head
            metadata = self._extract_metadata(assets.seo_head)
            
            # Check if page exists and get current checksum
            self.cur.execute(
                "SELECT markdown_checksum FROM pages WHERE url = %s",
                (assets.url,)
            )
            result = self.cur.fetchone()
            
            if result is None:
                # Insert new page
                self.cur.execute(
                    """
                    INSERT INTO pages (
                        url, title, clean_text, raw_html, markdown_checksum, 
                        markdown_changed, metadata, last_seen
                    ) VALUES (%s, %s, %s, %s, %s, NOW(), %s, NOW())
                    """,
                    (
                        assets.url, assets.title, assets.clean_text, assets.raw_html,
                        markdown_cs, json.dumps(metadata)
                    )
                )
                self.conn.commit()
                return True, False  # content_changed=True, seo_changed=False
            else:
                # Update existing page if content changed
                old_checksum = result[0]
                if old_checksum != markdown_cs:
                    self.cur.execute(
                        """
                        UPDATE pages SET 
                            title = %s, clean_text = %s, raw_html = %s,
                            markdown_checksum = %s, markdown_changed = NOW(),
                            metadata = %s, last_seen = NOW()
                        WHERE url = %s
                        """,
                        (
                            assets.title, assets.clean_text, assets.raw_html,
                            markdown_cs, json.dumps(metadata), assets.url
                        )
                    )
                    self.conn.commit()
                    return True, False  # content_changed=True, seo_changed=False
                else:
                    # Only update last_seen if content hasn't changed
                    self.cur.execute(
                        "UPDATE pages SET last_seen = NOW() WHERE url = %s",
                        (assets.url,)
                    )
                    self.conn.commit()
                    return False, False  # content_changed=False, seo_changed=False
        except Exception as e:
            print(f"[ERROR] Exception in upsert_page: {e}")
            raise

    def pages_for_embedding(self) -> list[tuple[str, str]]:
        """
        Get pages that need embedding.
        
        This method queries the database for pages that have not yet
        been embedded (summary_vec is NULL).
        
        Returns:
            List of (url, clean_text) tuples for pages needing embedding
            
        Example:
            >>> storage = PostgresStorage(db_cfg)
            >>> pages = storage.pages_for_embedding()
            >>> for url, text in pages:
            ...     print(f"Need to embed: {url}")
        """
        self.cur.execute(
            "SELECT url, clean_text FROM pages WHERE summary_vec IS NULL"
        )
        return self.cur.fetchall()

    def save_vectors(self, url: str, vecs: list[list[float]]) -> None:
        """
        Save page and chunk vectors.
        
        This method:
        1. Computes page vector as mean of chunk vectors
        2. Updates the page's summary vector
        3. Stores individual chunk vectors
        
        Args:
            url: The URL of the page
            vecs: List of chunk vectors to store
            
        Example:
            >>> storage = PostgresStorage(db_cfg)
            >>> # Save vectors for a page with 3 chunks
            >>> vecs = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
            >>> storage.save_vectors("https://example.com", vecs)
        """
        # page-level vector = mean of chunk vectors
        import numpy as np
        page_vec = np.mean(vecs, axis=0).tolist()

        # store page vector
        self.cur.execute(
            "UPDATE pages SET summary_vec = %s, embedded_at = NOW() WHERE url = %s",
            (page_vec, url),
        )

        # store chunk vectors
        from psycopg2.extras import execute_values
        rows = [(url, idx, vec) for idx, vec in enumerate(vecs)]
        execute_values(
            self.cur,
            "INSERT INTO chunks (page_url, chunk_index, vec) VALUES %s",
            rows,
        ) 