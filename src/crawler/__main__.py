"""
src.crawler.__main__
====================

Command‑line entry point for the crawler package.

Example
-------
    python -m src.crawler https://www.example.com
"""

import sys
import asyncio
from .crawler import Crawler

def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m src.crawler https://example.com")
        sys.exit(1)

    start_url = Crawler.canonical(sys.argv[1])
    crawler = Crawler()
    asyncio.run(crawler.crawl(start_url))

if __name__ == "__main__":  # pragma: no cover
    main()