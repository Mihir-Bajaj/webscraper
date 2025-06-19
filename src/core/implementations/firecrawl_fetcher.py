"""
Firecrawl-backed implementation of the Fetcher interface.

• Posts a URL to /v1/scrape
• Returns html, markdown, and links directly
"""

from __future__ import annotations
import aiohttp, asyncio, base64
from typing import Any, Dict
from src.core.interfaces.fetcher import Fetcher, FetchResult

# Default Firecrawl URL - can be overridden via set_firecrawl_url()
FIRECRAWL_URL = "http://localhost:3002/v1"

class FirecrawlFetcher(Fetcher):
    def __init__(self, session: aiohttp.ClientSession, poll_delay: float = 1.0, max_retries: int = 3, rate_limit: float = 0.2):
        super().__init__(concurrency=1)          # parent uses this attr
        self._session = session
        self._delay   = poll_delay
        self._firecrawl_url = FIRECRAWL_URL
        self._max_retries = max_retries
        self._rate_limit = rate_limit  # seconds between requests (reduced from 0.5 to 0.2)
        self._last_request_time = 0
        self._request_semaphore = asyncio.Semaphore(8)  # Increased from 3 to 8 concurrent requests

    def set_firecrawl_url(self, url: str):
        """Set the Firecrawl server URL."""
        self._firecrawl_url = url

    async def _rate_limit_request(self):
        """Ensure we don't exceed rate limits."""
        now = asyncio.get_event_loop().time()
        time_since_last = now - self._last_request_time
        if time_since_last < self._rate_limit:
            await asyncio.sleep(self._rate_limit - time_since_last)
        self._last_request_time = asyncio.get_event_loop().time()

    async def _scrape_url(self, url: str) -> Dict[str, Any]:
        """Scrape a single URL using the Firecrawl API with retry logic and rate limiting."""
        async with self._request_semaphore:  # Limit concurrent requests
            await self._rate_limit_request()  # Rate limiting
            
            body = {
                "url": url,
                "formats": ["html", "markdown", "links"],
                "onlyMainContent": True,
                "excludeTags": ["img", "video"],
                "fastMode": False
            }
            
            for attempt in range(self._max_retries):
                try:
                    # Add timeout to prevent hanging requests
                    timeout = aiohttp.ClientTimeout(total=60, connect=10)
                    async with self._session.post(f"{self._firecrawl_url}/scrape", json=body, timeout=timeout) as r:
                        if r.status == 200:
                            response = await r.json()
                            if response.get("success"):
                                return response.get("data", {})
                            else:
                                error_msg = response.get('error', 'Unknown error')
                                print(f"Firecrawl API failed for {url}: {error_msg}")
                                if attempt < self._max_retries - 1:
                                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                                    continue
                                raise Exception(f"Firecrawl API failed: {error_msg}")
                        else:
                            error_text = await r.text()
                            print(f"Firecrawl API error {r.status} for {url}: {error_text}")
                            if attempt < self._max_retries - 1:
                                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                                continue
                            raise Exception(f"Firecrawl API error {r.status}: {error_text}")
                            
                except asyncio.TimeoutError:
                    print(f"Timeout on attempt {attempt + 1} for {url}")
                    if attempt < self._max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        raise Exception(f"Request timeout after {self._max_retries} attempts for {url}")
                        
                except Exception as e:
                    if attempt < self._max_retries - 1:
                        print(f"Attempt {attempt + 1} failed for {url}: {e}")
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        raise e
            
            raise Exception(f"All {self._max_retries} attempts failed for {url}")

    async def get(self, url: str) -> str | None:        # keep AioHTTP-style name
        try:
            data = await self._scrape_url(url)
            
            # Return the HTML content
            html = data.get("html", "")
            return html
            
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    async def fetch(self, url: str) -> FetchResult:
        """Implement the Fetcher interface fetch method."""
        try:
            data = await self._scrape_url(url)
            
            html = data.get("html", "")
            markdown = data.get("markdown", "")
            links = data.get("links", [])
            
            # Pack markdown & links into FetchResult.extra for the parser
            return FetchResult(
                url          = url,
                content      = html,
                status_code  = 200,
                content_type = "text/html",
                extra        = {"markdown": markdown, "links": links},
            )
            
        except Exception as e:
            return FetchResult(
                url=url,
                content="",
                status_code=500,
                error=f"Firecrawl scrape failed: {str(e)}"
            )