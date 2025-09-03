"""
Concurrent BFS crawler using pluggable Fetcher, Parser, Storage.

This crawler implements a breadth-first search (BFS) algorithm to crawl websites,
processing pages level by level. It uses asynchronous programming for efficient
concurrent fetching of pages.

Example:
    ```python
    # Create and run a crawler
    crawler = Crawler()
    await crawler.crawl("https://example.com")
    
    # The crawler will:
    # 1. Start at example.com
    # 2. Extract all links on the page
    # 3. Visit each link at depth 1
    # 4. Continue until max_depth or max_pages is reached
    ```
"""
# Importing necessary libraries
import asyncio  # Used for asynchronous programming
from typing import List, Set, Tuple, Optional, Dict  # Type hints for Python
from urllib.parse import urljoin, urlparse, urldefrag  # Tools for URL handling
from bs4 import BeautifulSoup  # Library for parsing HTML
import logging  # For logging messages and errors
import aiohttp
import importlib

# Importing configuration from settings file
from src.config.settings import (
    FETCHER_CLS_NAME,  # Class name for fetching web pages
    PARSER_CLS_NAME,   # Class name for parsing HTML content
    STORAGE_CLS_NAME,  # Class name for storing crawled data
    REST_API_CONFIG,  # REST API configuration
    CRAWLER_CONFIG,  # Crawler settings like depth and concurrency
)

# Setting up logging to track what the crawler is doing
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_class_from_name(class_name: str):
    """Dynamically import a class from its full name"""
    module_name, class_name = class_name.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)

class Crawler:
    """
    A web crawler that implements breadth-first search with concurrent fetching.
    
    The crawler uses three main components:
    - Fetcher: Downloads web pages concurrently
    - Parser: Extracts content and links from HTML
    - Storage: Stores crawled data and tracks changes
    
    Attributes:
        fetcher: Component that handles HTTP requests
        parser: Component that parses HTML content
        store: Component that stores crawled data
        frontier: Set of URLs waiting to be processed
        depth_map: Dictionary mapping URLs to their crawl depth
        processed: Set of URLs that have been processed
    """
    
    def __init__(self):
        """
        Initialize the crawler with its components and data structures.
        
        The crawler is configured using settings from CRAWLER_CONFIG and REST_API_CONFIG.
        """
        # Initialize the crawler components
        self.fetcher_cls = get_class_from_name(FETCHER_CLS_NAME)  # Store fetcher class for dynamic instantiation
        self.parser = get_class_from_name(PARSER_CLS_NAME)()  # Parses HTML content
        self.store = get_class_from_name(STORAGE_CLS_NAME)(REST_API_CONFIG)  # Stores crawled data via REST API
        self.frontier: Set[str] = set()  # Set of URLs waiting to be processed
        self.depth_map: Dict[str, int] = {}  # Maps URLs to their depth in the crawl
        self.processed: Set[str] = set()  # Set of URLs that have been processed

    @staticmethod
    def canonical(url: str) -> str:
        """
        Canonicalize a URL by standardizing its format.
        
        This method:
        1. Converts the domain to lowercase
        2. Removes URL fragments (parts after #)
        3. Removes trailing slashes
        4. Normalizes query parameters (sorts them for consistency)
        5. Handles www vs non-www domains consistently
        
        Args:
            url: The URL to canonicalize
            
        Returns:
            The canonicalized URL
            
        Example:
            >>> Crawler.canonical("https://Example.com/page/#section?param=value")
            'https://example.com/page?param=value'
            >>> Crawler.canonical("https://example.com/page/")
            'https://example.com/page'
            >>> Crawler.canonical("https://www.aezion.com/blogs/page/6/?et_blog")
            'https://aezion.com/blogs/page/6?et_blog'
        """
        from urllib.parse import parse_qs, urlencode
        
        # Parse the URL
        u = urlparse(url)
        
        # Normalize domain (remove www prefix and convert to lowercase)
        netloc = u.netloc.lower()
        if netloc.startswith('www.'):
            netloc = netloc[4:]  # Remove www prefix
        
        # Normalize query parameters
        if u.query:
            # Parse query parameters
            query_params = parse_qs(u.query)
            # Sort parameters for consistency
            sorted_params = dict(sorted(query_params.items()))
            # Rebuild query string
            query = urlencode(sorted_params, doseq=True)
        else:
            query = ""
        
        # Build canonicalized URL
        canonical_url = u._replace(
            netloc=netloc,
            query=query,
            fragment=""  # Remove the fragment (part after #)
        ).geturl()
        
        # Remove trailing slash (except for root URLs)
        if canonical_url != '/' and canonical_url != 'https://' and canonical_url != 'http://':
            canonical_url = canonical_url.rstrip('/')
        
        return canonical_url

    @staticmethod
    def is_same_domain(url1: str, url2: str) -> bool:
        """
        Check if two URLs are on the same domain, treating www and non-www as the same.
        
        Args:
            url1: First URL to compare
            url2: Second URL to compare
            
        Returns:
            True if both URLs are on the same domain
            
        Example:
            >>> Crawler.is_same_domain("https://aezion.com/page", "https://www.aezion.com/other")
            True
            >>> Crawler.is_same_domain("https://aezion.com/page", "https://other.com/page")
            False
        """
        def strip_www(netloc: str) -> str:
            """Remove www. prefix from domain if present."""
            return netloc.lower().lstrip('www.')
        
        try:
            domain1 = strip_www(urlparse(url1).netloc)
            domain2 = strip_www(urlparse(url2).netloc)
            return domain1 == domain2
        except Exception:
            return False

    @staticmethod
    def is_crawlable_url(url: str) -> bool:
        """
        Check if a URL is crawlable (valid HTTP/HTTPS URL).
        
        Args:
            url: The URL to check
            
        Returns:
            True if the URL is crawlable
            
        Example:
            >>> Crawler.is_crawlable_url("https://example.com/page")
            True
            >>> Crawler.is_crawlable_url("javascript:void(0)")
            False
            >>> Crawler.is_crawlable_url("tel:+1234567890")
            False
        """
        return url.startswith("http://") or url.startswith("https://")

    @staticmethod
    def same_domain_links(base: str, html: str) -> List[str]:
        """
        Extract and canonicalize links from HTML that are on the same domain.
        
        This method:
        1. Parses the HTML using BeautifulSoup
        2. Finds all <a> tags with href attributes
        3. Converts relative URLs to absolute URLs
        4. Filters out external links and special URLs
        5. Canonicalizes the remaining URLs
        
        Args:
            base: The base URL of the page being processed
            html: The HTML content of the page
            
        Returns:
            A list of canonicalized URLs on the same domain
            
        Example:
            >>> html = '''
            ... <a href="/about">About</a>
            ... <a href="https://example.com/contact">Contact</a>
            ... <a href="https://other.com">External</a>
            ... <a href="javascript:void(0)">JS Link</a>
            ... '''
            >>> Crawler.same_domain_links("https://example.com", html)
            ['https://example.com/about', 'https://example.com/contact']
        """
        # Parse the HTML content
        soup = BeautifulSoup(html, "lxml")
        # Get the domain of the base URL
        base_domain = urlparse(base).netloc
        links = set()  # Use set to avoid duplicates
        
        # Find all links (<a> tags with href attribute)
        all_links = soup.find_all("a", href=True)
        
        for a in all_links:
            # Remove the fragment from the href
            href = urldefrag(a["href"])[0]
            # Skip empty links or special links like javascript:, mailto:, etc.
            if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
                
            try:
                # Convert relative URLs to absolute URLs
                abs_url = urljoin(base, href)
                # Standardize the URL format
                canonical_url = Crawler.canonical(abs_url)
                
                # Only keep links that are on the same domain
                if urlparse(canonical_url).netloc == base_domain:
                    links.add(canonical_url)
            except Exception as e:
                # Log any errors that occur during URL processing
                continue
        
        return list(links)

    async def process_page(self, url: str, fetch_result, depth: int) -> None:
        """
        Process a single page: store its content and collect its links.
        
        This method:
        1. Parses the page content using the parser component
        2. Stores the page data and checks for changes
        3. Extracts links if we haven't reached max depth
        4. Adds new links to the frontier
        
        Args:
            url: The URL of the page being processed
            fetch_result: The FetchResult containing HTML and extra data
            depth: The current depth in the crawl
        """
        # Skip if we couldn't fetch the page
        if fetch_result is None or fetch_result.error:
            print(f"❌ FAIL {url}")
            return

        # Use the parser to extract assets (text, images, etc.) from the page
        # Pass the extra data (markdown, links) to the parser
        assets = self.parser.parse(url, fetch_result.content, fetch_result.extra)
        # Store the page data and check if content or SEO elements changed
        content_changed, seo_changed = self.store.upsert_page(assets)

        # Show simple pass/fail status
        if content_changed or seo_changed:
            print(f"✅ PASS {url}")
        elif content_changed is False and seo_changed is False:
            print(f"❌ FAIL {url} (storage failed)")
        else:
            print(f"✅ PASS {url} (no changes)")

        # Only look for new links if we haven't reached max depth
        if depth + 1 <= CRAWLER_CONFIG["max_depth"]:
            # Use links from Firecrawl if available, otherwise extract from HTML
            if fetch_result.extra and "links" in fetch_result.extra:
                firecrawl_links = fetch_result.extra["links"]
                # Filter Firecrawl links to same domain and ensure they're crawlable
                new_links = []
                for link in firecrawl_links:
                    try:
                        # Skip non-crawlable URLs (javascript:, tel:, mailto:, etc.)
                        if not self.is_crawlable_url(link):
                            continue
                        
                        canonical_link = self.canonical(link)
                        if self.is_same_domain(canonical_link, url):
                            new_links.append(canonical_link)
                    except Exception as e:
                        continue
            else:
                # Fallback to extracting links from HTML
                new_links = self.same_domain_links(url, fetch_result.content)
            
            # Add new links to frontier
            for link in new_links:
                # Only add to frontier if we haven't processed it yet and haven't seen it before
                if link not in self.processed and link not in self.frontier:
                    self.frontier.add(link)
                    self.depth_map[link] = depth + 1

    async def _crawl_loop(self, fetcher, start_url: str) -> None:
        """
        Internal method to run the BFS crawl loop using the provided fetcher.
        """
        # Standardize the starting URL
        start_url = self.canonical(start_url)
        # Initialize data structures
        self.frontier = {start_url}  # URLs to process
        self.depth_map = {start_url: 0}  # Track depth of each URL
        self.processed = set()  # URLs we've already processed
        current_depth = 0  # Start at depth 0

        print(f"🚀 Starting crawl: {start_url}")
        print(f"📊 Max depth: {CRAWLER_CONFIG['max_depth']}, Max pages: {CRAWLER_CONFIG['max_pages']}\n")

        # Continue crawling until we run out of URLs, reach max depth, or process max pages
        while (self.frontier and 
               current_depth <= CRAWLER_CONFIG["max_depth"] and 
               len(self.processed) < CRAWLER_CONFIG["max_pages"]):
            
            # Get all URLs at the current depth level (BFS approach)
            batch = {url for url in self.frontier if self.depth_map[url] == current_depth}
            if not batch:
                # If no URLs at current depth, move to next depth
                current_depth += 1
                continue

            # Remove batch URLs from the frontier
            self.frontier -= batch

            # Fetch all URLs in the batch concurrently
            fetch_results = await asyncio.gather(*(fetcher.fetch(u) for u in batch))

            # Process each fetched page
            for url, fetch_result in zip(batch, fetch_results):
                if fetch_result is not None and not fetch_result.error:
                    await self.process_page(url, fetch_result, current_depth)
                else:
                    # Mark as failed if fetch failed
                    print(f"❌ FAIL {url} (fetch failed)")
                self.processed.add(url)  # Mark as processed regardless of fetch result

            # Wait before next batch (to be polite to servers)
            await asyncio.sleep(CRAWLER_CONFIG["crawl_delay"])
            
            # Print progress information
            print(f"📈 Depth {current_depth}: {len(self.frontier)} pending, {len(self.processed)} processed")

            # Check if we need to move to the next depth
            if not any(self.depth_map[url] == current_depth for url in self.frontier):
                current_depth += 1

        print(f"\n✅ Crawl complete: {len(self.processed)} pages processed")
        
        # Flush any remaining pages in the batch buffer
        if hasattr(self.store, 'flush_all'):
            self.store.flush_all()

    async def crawl(self, start_url: str) -> None:
        """
        Crawl a website starting from the given URL using BFS.
        
        This method:
        1. Initializes the crawl with the start URL
        2. Processes pages level by level (BFS)
        3. Fetches multiple pages concurrently
        4. Respects crawl delay between batches
        5. Stops when max depth or max pages is reached
        
        Args:
            start_url: The URL to start crawling from
            
        Example:
            >>> crawler = Crawler()
            >>> await crawler.crawl("https://example.com")
            # Will crawl example.com and its subpages:
            # Depth 0: example.com
            # Depth 1: example.com/about, example.com/contact
            # Depth 2: example.com/about/team, example.com/contact/form
            # etc.
        """
        async with aiohttp.ClientSession() as session:
            fetcher = self.fetcher_cls(session)
            await self._crawl_loop(fetcher, start_url)

# Entry point function when script is run directly
async def main():
    """
    Main entry point for the crawler script.
    
    This function:
    1. Checks for a URL argument
    2. Creates a crawler instance
    3. Starts the crawl
    
    Example:
        $ python -m src.crawler.crawler https://example.com
        # Will start crawling example.com
    """
    import sys
    # Check if URL argument is provided
    if len(sys.argv) != 2:
        print("Usage: python -m src.crawler.crawler https://example.com")
        sys.exit(1)

    # Create crawler and start crawling from the provided URL
    crawler = Crawler()
    await crawler.crawl(sys.argv[1])

# Run the main function when script is executed directly
if __name__ == "__main__":
    asyncio.run(main())  # Run the async main function 