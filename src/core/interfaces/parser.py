"""
Parser interface for the webscraper project.

This module defines the interface for parsing web pages in the crawler.
It provides a protocol for implementing different parsing strategies
and a data class for storing parsed page assets.

Example:
    ```python
    class MyParser(Parser):
        def parse(self, url: str, html: str) -> PageAssets:
            # Implementation here
            return PageAssets(
                url=url,
                raw_html=html,
                clean_text="Extracted text...",
                seo_head="SEO elements...",
                title="Page title"
            )
    ```
"""
from typing import Protocol, NamedTuple

class PageAssets(NamedTuple):
    """
    Container for parsed page data.
    
    This class holds the various components extracted from a web page,
    including raw HTML, cleaned text, SEO elements, and metadata.
    
    Attributes:
        url: The URL of the parsed page
        raw_html: The original HTML content
        clean_text: Extracted and cleaned text content
        seo_head: SEO-related elements from the head section
        title: The page title
        
    Example:
        >>> assets = PageAssets(
        ...     url="https://example.com",
        ...     raw_html="<html>...</html>",
        ...     clean_text="Main content...",
        ...     seo_head="<title>Example</title>",
        ...     title="Example Page"
        ... )
        >>> assets.title
        'Example Page'
    """
    url: str
    raw_html: str
    clean_text: str
    seo_head: str
    title: str

class Parser(Protocol):
    """
    Interface for parsing web pages.
    
    This protocol defines the interface that all parser implementations
    must follow. It allows for different parsing strategies while
    maintaining a consistent interface for extracting page assets.
    
    Example:
        ```python
        class HTMLParser(Parser):
            def parse(self, url: str, html: str) -> PageAssets:
                soup = BeautifulSoup(html, "lxml")
                return PageAssets(
                    url=url,
                    raw_html=html,
                    clean_text=soup.get_text(),
                    seo_head=str(soup.head),
                    title=soup.title.string if soup.title else ""
                )
        ```
    """
    
    def parse(self, url: str, html: str) -> PageAssets:
        """
        Parse HTML into structured page assets.
        
        This method should be implemented to extract various components
        from the HTML content and return them as a PageAssets object.
        
        Args:
            url: The URL of the page being parsed
            html: The HTML content to parse
            
        Returns:
            PageAssets containing the parsed components
            
        Example:
            >>> parser = MyParser()
            >>> html = "<html><head><title>Example</title></head><body>Content</body></html>"
            >>> assets = parser.parse("https://example.com", html)
            >>> assets.title
            'Example'
            >>> assets.clean_text
            'Content'
        """
        ... 