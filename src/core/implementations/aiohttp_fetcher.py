"""
Aiohttp-based implementation of the Fetcher interface.

This module provides an asynchronous HTTP client implementation using aiohttp.
It supports concurrent fetching with rate limiting and proper session management.

Example:
    ```python
    async with AiohttpFetcher(concurrency=4) as fetcher:
        # Fetch a single URL
        html = await fetcher.get("https://example.com")
        
        # Or use the Fetcher interface
        result = await fetcher.fetch("https://example.com")
        if result.status_code == 200:
            print(result.content)
    ```
"""
import asyncio
from typing import Optional, Dict
import aiohttp
from src.core.interfaces.fetcher import Fetcher, FetchResult

class AiohttpFetcher(Fetcher):
    """
    Asynchronous HTTP client using aiohttp.
    
    This implementation:
    1. Uses aiohttp for efficient async HTTP requests
    2. Implements rate limiting via semaphore
    3. Manages a single session for all requests
    4. Handles connection errors gracefully
    
    Attributes:
        semaphore: Limits concurrent requests
        session: The aiohttp client session
        
    Example:
        ```python
        # Create a fetcher with max 4 concurrent requests
        fetcher = AiohttpFetcher(concurrency=4)
        
        # Use as async context manager
        async with fetcher:
            html = await fetcher.get("https://example.com")
        ```
    """
    
    def __init__(self, concurrency: int = 20):
        """
        Initialize the fetcher with specified concurrency limit.
        
        Args:
            concurrency: Maximum number of concurrent requests (default: 8)
            
        Example:
            >>> fetcher = AiohttpFetcher(concurrency=4)
            >>> fetcher.semaphore._value
            4
        """
        self.semaphore = asyncio.Semaphore(concurrency)
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """
        Set up the aiohttp session when entering async context.
        
        Returns:
            The fetcher instance
            
        Example:
            >>> async with AiohttpFetcher() as fetcher:
            ...     assert fetcher.session is not None
        """
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Clean up the aiohttp session when exiting async context.
        
        Example:
            >>> async with AiohttpFetcher() as fetcher:
            ...     pass  # Session will be closed automatically
        """
        await self.close()

    async def close(self):
        """
        Close the aiohttp session.
        
        This method should be called to properly clean up resources
        when the fetcher is no longer needed.
        
        Example:
            >>> fetcher = AiohttpFetcher()
            >>> await fetcher.close()  # Clean up resources
        """
        if self.session:
            await self.session.close()
            self.session = None

    async def get(self, url: str) -> Optional[str]:
        """
        Fetch a URL using aiohttp.
        
        This method:
        1. Ensures a session exists
        2. Respects the concurrency limit
        3. Handles errors gracefully
        4. Returns the response text for successful requests
        
        Args:
            url: The URL to fetch
            
        Returns:
            The response text if successful, None otherwise
            
        Example:
            >>> async with AiohttpFetcher() as fetcher:
            ...     html = await fetcher.get("https://example.com")
            ...     if html:
            ...         print("Success!")
            ...     else:
            ...         print("Failed to fetch")
        """
        if not self.session:
            self.session = aiohttp.ClientSession()

        async with self.semaphore:
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        return await response.text()
            except Exception as e:
                print(f"Error fetching {url}: {e}")
            return None 