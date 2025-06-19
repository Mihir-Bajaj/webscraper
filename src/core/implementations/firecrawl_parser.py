"""
Firecrawl-aware Parser that pulls markdown & checksum
"""

import hashlib
from src.core.interfaces.parser import Parser, PageAssets
from src.core.interfaces.fetcher import FetchResult

class FirecrawlParser(Parser):
    def parse(self, url: str, html: str, extra: dict | None = None) -> PageAssets:
        if extra is None or "markdown" not in extra:
            raise ValueError("FirecrawlParser expects markdown in FetchResult.extra")

        markdown = extra["markdown"]
        links    = extra.get("links", [])
        checksum = hashlib.sha256(markdown.encode()).hexdigest()

        return PageAssets(
            url         = url,
            raw_html    = html,
            clean_text  = markdown,
            seo_head    = "",           # optional: store JSON metadata
            title       = "",           # you can parse <title> later
            checksum    = checksum,
            links       = links         # add `links` attr if PageAssets supports it
        )