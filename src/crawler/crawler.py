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

# Importing configuration from settings file
from src.config.settings import (
    FETCHER_CLS,  # Class that handles fetching web pages
    PARSER_CLS,   # Class that parses HTML content
    STORAGE_CLS,  # Class that stores crawled data
    DB_CONFIG,    # Database configuration
    CRAWLER_CONFIG,  # Crawler settings like depth and concurrency
)

# Setting up logging to track what the crawler is doing
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        
        The crawler is configured using settings from CRAWLER_CONFIG and DB_CONFIG.
        """
        # Initialize the crawler components
        self.fetcher = FETCHER_CLS(concurrency=CRAWLER_CONFIG["concurrency"])  # Handles multiple concurrent requests
        self.parser = PARSER_CLS()  # Parses HTML content
        self.store = STORAGE_CLS(DB_CONFIG)  # Stores crawled data
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
        4. Preserves query parameters
        
        Args:
            url: The URL to canonicalize
            
        Returns:
            The canonicalized URL
            
        Example:
            >>> Crawler.canonical("https://Example.com/page/#section?param=value")
            'https://example.com/page?param=value'
            >>> Crawler.canonical("https://example.com/page/")
            'https://example.com/page'
        """
        # This makes different versions of the same URL look the same
        # (e.g., example.com/ and example.com are treated as identical)
        u = urlparse(url)
        # Keep query parameters as they might be important for some sites
        return u._replace(
            netloc=u.netloc.lower(),  # Convert domain to lowercase
            fragment=""  # Remove the fragment (part after #)
        ).geturl().rstrip("/")  # Remove trailing slash

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
        logger.info(f"Found {len(all_links)} total links on {base}")
        
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
                    logger.debug(f"Found same-domain link: {canonical_url}")
                else:
                    logger.debug(f"Skipping external link: {canonical_url}")
            except Exception as e:
                # Log any errors that occur during URL processing
                logger.warning(f"Error processing link {href}: {e}")
                continue
        
        logger.info(f"Found {len(links)} unique same-domain links on {base}")
        return list(links)

    async def process_page(self, url: str, html: str, depth: int) -> None:
        """
        Process a single page: store its content and collect its links.
        
        This method:
        1. Parses the page content using the parser component
        2. Stores the page data and checks for changes
        3. Extracts links if we haven't reached max depth
        4. Adds new links to the frontier
        
        Args:
            url: The URL of the page being processed
            html: The HTML content of the page
            depth: The current depth in the crawl
            
        Example:
            >>> await crawler.process_page(
            ...     "https://example.com",
            ...     "<html><body><a href='/about'>About</a></body></html>",
            ...     0
            ... )
            # Will:
            # 1. Parse and store the page content
            # 2. Extract the /about link
            # 3. Add https://example.com/about to the frontier
        """
        # Skip if we couldn't fetch the page
        if html is None:
            logger.warning(f"Failed to fetch {url}")
            return

        logger.info(f"Processing page at depth {depth}: {url}")
        
        # Use the parser to extract assets (text, images, etc.) from the page
        assets = self.parser.parse(url, html)
        # Store the page data and check if content or SEO elements changed
        content_changed, seo_changed = self.store.upsert_page(assets)

        # Log status with symbols for content and SEO changes
        status = []
        if content_changed:
            status.append("EMBD")  # Content/embedding changed
        else:
            status.append("----")  # No content change
        if seo_changed:
            status.append("SEO")  # SEO elements changed
        print(f"{' '.join(status):<8} {url}", flush=True)

        # Only look for new links if we haven't reached max depth
        if depth + 1 <= CRAWLER_CONFIG["max_depth"]:
            # Extract links from the HTML
            new_links = self.same_domain_links(url, html)
            logger.info(f"Found {len(new_links)} new links on {url}")
            
            added_count = 0
            for link in new_links:
                # Only add to frontier if we haven't processed it yet and haven't seen it before
                if link not in self.processed and link not in self.frontier:
                    self.frontier.add(link)
                    self.depth_map[link] = depth + 1
                    added_count += 1
                    logger.debug(f"Added to frontier: {link} at depth {depth + 1}")
            
            logger.info(f"Added {added_count} new URLs to frontier from {url}")

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
        # Standardize the starting URL
        start_url = self.canonical(start_url)
        # Initialize data structures
        self.frontier = {start_url}  # URLs to process
        self.depth_map = {start_url: 0}  # Track depth of each URL
        self.processed = set()  # URLs we've already processed
        current_depth = 0  # Start at depth 0

        logger.info(f"Starting crawl from {start_url}")
        logger.info(f"Max depth: {CRAWLER_CONFIG['max_depth']}")
        logger.info(f"Max pages: {CRAWLER_CONFIG['max_pages']}")

        # Set up the fetcher context
        async with self.fetcher:
            # Continue crawling until we run out of URLs, reach max depth, or process max pages
            while (self.frontier and 
                   current_depth <= CRAWLER_CONFIG["max_depth"] and 
                   len(self.processed) < CRAWLER_CONFIG["max_pages"]):
                
                # Get all URLs at the current depth level (BFS approach)
                batch = {url for url in self.frontier if self.depth_map[url] == current_depth}
                if not batch:
                    # If no URLs at current depth, move to next depth
                    logger.info(f"No more URLs at depth {current_depth}, moving to next depth")
                    current_depth += 1
                    continue

                # Remove batch URLs from the frontier
                self.frontier -= batch
                logger.info(f"Processing {len(batch)} URLs at depth {current_depth}")
                logger.info(f"Frontier size: {len(self.frontier)}, Total processed: {len(self.processed)}")

                # Fetch all URLs in the batch concurrently
                htmls = await asyncio.gather(*(self.fetcher.get(u) for u in batch))

                # Process each fetched page
                for url, html in zip(batch, htmls):
                    if html is not None:  # Only process if fetch was successful
                        await self.process_page(url, html, current_depth)
                    self.processed.add(url)  # Mark as processed regardless of fetch result

                # Wait before next batch (to be polite to servers)
                await asyncio.sleep(CRAWLER_CONFIG["crawl_delay"])
                
                # Print progress information
                print(f"\nDepth {current_depth}: {len(self.frontier)} URLs in frontier, {len(self.processed)} URLs processed")
                logger.info(f"Depth {current_depth} complete. Frontier: {len(self.frontier)}, Processed: {len(self.processed)}")

                # Check if we need to move to the next depth
                if not any(self.depth_map[url] == current_depth for url in self.frontier):
                    current_depth += 1
                    logger.info(f"Moving to depth {current_depth}")

        logger.info(f"Crawl complete. Total pages processed: {len(self.processed)}")

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