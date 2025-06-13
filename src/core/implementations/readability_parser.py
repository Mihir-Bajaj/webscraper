"""
Readability-based implementation of the Parser interface.

This module provides a web page parser implementation using the readability-lxml
library. It extracts clean text content, titles, and SEO elements from HTML
while removing clutter like ads and navigation.

Example:
    ```python
    # Create a parser
    parser = ReadabilityParser()
    
    # Parse a web page
    html = "<html><head><title>Example</title></head><body>Content</body></html>"
    assets = parser.parse("https://example.com", html)
    
    print(assets.title)  # "Example"
    print(assets.clean_text)  # "Content"
    ```
"""
from readability import Document
from bs4 import BeautifulSoup
from src.core.interfaces.parser import Parser, PageAssets
from src.core.checksum import content_and_hash

class ReadabilityParser(Parser):
    """
    Extracts title, clean text, and <head> HTML using readability-lxml.
    
    This implementation uses the readability-lxml library to extract
    the main content from web pages while removing clutter. It also
    preserves important SEO elements from the head section.
    
    The parser:
    1. Extracts the page title
    2. Gets clean text content using readability
    3. Preserves SEO elements from the head section
    4. Maintains the original HTML for reference
    
    Example:
        ```python
        parser = ReadabilityParser()
        html = '''
            <html>
            <head>
                <title>Example Page</title>
                <meta name="description" content="Example">
            </head>
            <body>
                <nav>Menu</nav>
                <article>Main content</article>
                <footer>Footer</footer>
            </body>
            </html>
        '''
        assets = parser.parse("https://example.com", html)
        print(assets.title)  # "Example Page"
        print(assets.clean_text)  # "Main content"
        ```
    """
    
    def parse(self, url: str, html: str) -> PageAssets:
        """
        Parse HTML into structured page assets.
        
        This method:
        1. Extracts the page title using readability
        2. Gets clean text content using the checksum module
        3. Preserves the head section for SEO elements
        4. Returns all components in a PageAssets object
        
        Args:
            url: The URL of the page being parsed
            html: The HTML content to parse
            
        Returns:
            PageAssets containing the parsed components
            
        Example:
            >>> parser = ReadabilityParser()
            >>> html = "<html><head><title>Test</title></head><body>Content</body></html>"
            >>> assets = parser.parse("https://example.com", html)
            >>> assets.title
            'Test'
            >>> assets.clean_text
            'Content'
            >>> assets.seo_head
            '<head><title>Test</title></head>'
        """
        title = Document(html).short_title().strip()
        clean_text, _ = content_and_hash(html)          # reuse existing logic
        soup = BeautifulSoup(html, "lxml")
        seo_head = soup.head.decode() if soup.head else ""
        return PageAssets(
            url=url,
            raw_html=html,
            clean_text=clean_text,
            seo_head=seo_head,
            title=title,
        ) 