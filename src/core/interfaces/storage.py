"""
Storage interface for the webscraper project.

This module defines the interface for storing and retrieving page data
in the crawler. It provides a protocol for implementing different storage
backends (e.g., database, file system) while maintaining a consistent interface.

Example:
    ```python
    class DatabaseStorage(Storage):
        def upsert_page(self, assets: PageAssets) -> Tuple[bool, bool]:
            # Implementation here
            return (True, False)  # content changed, HTML unchanged
    ```
"""
from typing import Protocol, Tuple
from src.core.interfaces.parser import PageAssets

class Storage(Protocol):
    """
    Interface for storing and retrieving page data.
    
    This protocol defines the interface that all storage implementations
    must follow. It allows for different storage backends while
    maintaining a consistent interface for page data persistence.
    
    Example:
        ```python
        class PostgreSQLStorage(Storage):
            def __init__(self, connection_params: dict):
                self.conn = psycopg2.connect(**connection_params)
                
            def upsert_page(self, assets: PageAssets) -> Tuple[bool, bool]:
                # Store page data in PostgreSQL
                # Return change flags
                return (True, False)
        ```
    """
    
    def upsert_page(self, assets: PageAssets) -> Tuple[bool, bool]:
        """
        Store or update page data.
        
        This method should be implemented to store or update page data
        in the storage backend. It should also track changes in content
        and HTML structure.
        
        Args:
            assets: The page assets to store or update
            
        Returns:
            Tuple of (content_changed, html_changed) where:
            - content_changed: True if the page content has changed
            - html_changed: True if the HTML structure has changed
            
        Example:
            >>> storage = MyStorage()
            >>> assets = PageAssets(
            ...     url="https://example.com",
            ...     raw_html="<html>...</html>",
            ...     clean_text="Content",
            ...     seo_head="<title>Example</title>",
            ...     title="Example"
            ... )
            >>> content_changed, html_changed = storage.upsert_page(assets)
            >>> content_changed
            True
            >>> html_changed
            False
        """
        ... 