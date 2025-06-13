"""
PostgreSQL-based implementation of the Storage interface.

This module provides a storage implementation using PostgreSQL to store
and manage web page data, including content, checksums, and embeddings.

The implementation:
1. Stores page content and metadata
2. Tracks content and HTML changes
3. Manages page and chunk embeddings
4. Uses efficient bulk operations

Example:
    ```python
    # Create storage with database config
    storage = PostgresStorage({
        "dbname": "webscraper",
        "user": "postgres",
        "password": "secret"
    })
    
    # Store page data
    content_changed, html_changed = storage.upsert_page(assets)
    ```
"""
import psycopg2
from src.core.interfaces.storage import Storage
from src.core.interfaces.parser import PageAssets
from src.core.checksum import content_and_hash, compute_head_checksum

class PostgresStorage(Storage):
    """
    PostgreSQL-based storage implementation.
    
    This implementation uses PostgreSQL to store:
    1. Page content and metadata
    2. Content and HTML checksums
    3. Change timestamps
    4. Page and chunk embeddings
    
    The storage tracks changes in both content and HTML structure,
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
        content_changed, html_changed = storage.upsert_page(assets)
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

    def upsert_page(self, assets: PageAssets) -> tuple[bool, bool]:
        """
        Store or update page data.
        
        This method:
        1. Computes content and HTML checksums
        2. Inserts new pages if they don't exist
        3. Updates existing pages and tracks changes
        4. Returns change flags
        
        Args:
            assets: The page assets to store or update
            
        Returns:
            Tuple of (content_changed, html_changed) where:
            - content_changed: True if the page content has changed
            - html_changed: True if the HTML structure has changed
            
        Example:
            >>> storage = PostgresStorage(db_cfg)
            >>> assets = PageAssets(
            ...     url="https://example.com",
            ...     title="Example",
            ...     clean_text="Content",
            ...     seo_head="<head>...</head>",
            ...     raw_html="<html>...</html>"
            ... )
            >>> content_changed, html_changed = storage.upsert_page(assets)
            >>> content_changed  # True for new pages
            True
        """
        # recompute checksums from raw_html
        clean_text, content_cs = content_and_hash(assets.raw_html)
        head_cs                = compute_head_checksum(assets.raw_html)

        # 1. insert brand-new row
        self.cur.execute(
            """
            INSERT INTO pages (
              url, title, clean_text,
              content_checksum, html_checksum,
              last_seen, content_changed, html_changed
            )
            VALUES (%s,%s,%s,%s,%s,NOW(),NOW(),NOW())
            ON CONFLICT (url) DO NOTHING
            RETURNING 1;
            """,
            (assets.url, assets.title, clean_text, content_cs, head_cs),
        )
        if self.cur.fetchone():
            return True, True        # both kinds changed (brand-new)

        # 2. compare to existing
        self.cur.execute(
            "SELECT content_checksum, html_checksum FROM pages WHERE url=%s",
            (assets.url,),
        )
        old_content, old_head = self.cur.fetchone()
        c_changed = old_content != content_cs
        h_changed = old_head    != head_cs

        # 3. update row + timestamps
        self.cur.execute(
            """
            UPDATE pages
            SET last_seen = NOW(),
                title     = %s,
                clean_text= %s,
                content_checksum = %s,
                html_checksum    = %s,
                content_changed  = CASE WHEN %s THEN NOW() ELSE content_changed END,
                html_changed     = CASE WHEN %s THEN NOW() ELSE html_changed  END
            WHERE url = %s
            """,
            (assets.title, clean_text, content_cs, head_cs,
             c_changed, h_changed, assets.url),
        )
        return c_changed, h_changed

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