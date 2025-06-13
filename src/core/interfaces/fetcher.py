"""
Interface for web content fetching.

This module defines the interface for fetching web content in the crawler.
It provides a protocol for implementing different fetching strategies
(e.g., HTTP, file system, mock) and a data class for fetch results.

Example:
    ```python
    class MyFetcher(Fetcher):
        async def fetch(self, url: str) -> FetchResult:
            # Implementation here
            return FetchResult(
                url=url,
                content="<html>...</html>",
                status_code=200,
                content_type="text/html"
            )
    ```
"""
from typing import Protocol, Optional
from dataclasses import dataclass

@dataclass
class FetchResult:
    """
    Result of a fetch operation.
    
    This class encapsulates the result of fetching content from a URL,
    including the content itself and associated metadata.
    
    Attributes:
        url: The URL that was fetched
        content: The fetched content (HTML, text, etc.)
        status_code: HTTP status code or equivalent
        content_type: MIME type of the content (optional)
        error: Error message if the fetch failed (optional)
        
    Example:
        >>> result = FetchResult(
        ...     url="https://example.com",
        ...     content="<html>Hello</html>",
        ...     status_code=200,
        ...     content_type="text/html"
        ... )
        >>> result.status_code
        200
    """
    url: str
    content: str
    status_code: int
    content_type: Optional[str] = None
    error: Optional[str] = None

class Fetcher(Protocol):
    """
    Protocol for fetching web content.
    
    This protocol defines the interface that all fetcher implementations
    must follow. It allows for different fetching strategies while
    maintaining a consistent interface.
    
    Example:
        ```python
        class HTTPFetcher(Fetcher):
            async def fetch(self, url: str) -> FetchResult:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        return FetchResult(
                            url=url,
                            content=await response.text(),
                            status_code=response.status,
                            content_type=response.headers.get("content-type")
                        )
        ```
    """
    
    async def fetch(self, url: str) -> FetchResult:
        """
        Fetch content from a URL.
        
        This method should be implemented to fetch content from the given URL
        and return a FetchResult containing the content and metadata.
        
        Args:
            url: The URL to fetch content from
            
        Returns:
            FetchResult containing the fetched content and metadata
            
        Example:
            >>> fetcher = MyFetcher()
            >>> result = await fetcher.fetch("https://example.com")
            >>> result.status_code
            200
            >>> result.content_type
            'text/html'
        """
        ... 