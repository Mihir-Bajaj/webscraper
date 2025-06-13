

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
from . import crawl, canonical

def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m src.crawler https://example.com")
        sys.exit(1)

    start_url = canonical(sys.argv[1])
    asyncio.run(crawl(start_url))

if __name__ == "__main__":  # pragma: no cover
    main()