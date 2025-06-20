"""
Hybrid Firecrawl + Readability parser implementation.

This module implements a hybrid parsing approach that combines:
1. Firecrawl for web scraping and markdown generation
2. Readability for accurate content extraction and stable checksums

The parser uses Firecrawl to fetch pages and generate markdown, but then
uses Readability on the raw HTML to extract clean, stable content for
embedding and change detection. This approach provides:
- High-quality markdown for display and metadata
- Stable content extraction for reliable change detection
- Reduced false positives from dynamic content

Example:
    ```python
    parser = FirecrawlParser()
    assets = parser.parse(
        "https://example.com",
        "<html>...</html>",
        {"markdown": "# Example\n\nContent", "links": ["https://example.com/about"]}
    )
    print(assets.clean_text)  # Clean content from Readability
    print(assets.seo_head)    # Markdown from Firecrawl
    ```
"""

import hashlib
import json
import re
from readability import Document
from bs4 import BeautifulSoup
from src.core.interfaces.parser import Parser, PageAssets
from src.core.interfaces.fetcher import FetchResult

class FirecrawlParser(Parser):
    def parse(self, url: str, html: str, extra: dict | None = None) -> PageAssets:
        if extra is None or "markdown" not in extra:
            raise ValueError("FirecrawlParser expects markdown in FetchResult.extra")

        markdown = extra["markdown"]
        links = extra.get("links", [])
        metadata = extra.get("metadata", {})
        
        # Extract title from Firecrawl metadata first (most reliable)
        title = ""
        if metadata and "title" in metadata:
            title = metadata["title"].strip()
        
        # If no title in metadata, try to extract from markdown (first line that starts with #)
        if not title:
            for line in markdown.split('\n'):
                line = line.strip()
                if line.startswith('# '):
                    title = line[2:].strip()
                    break
        
        # If still no title, try to extract from HTML using readability
        if not title:
            try:
                title = Document(html).short_title().strip()
            except:
                title = ""
        
        # Use Readability to extract clean text from the HTML (more accurate than markdown processing)
        try:
            # Extract main content using readability
            main_html = Document(html).summary()
            soup_body = BeautifulSoup(main_html, "lxml")
            clean_text = soup_body.get_text(" ", strip=True)
            
            # Normalize whitespace
            clean_text = re.sub(r"\s+", " ", clean_text).strip()
        except Exception as e:
            # Fallback to markdown if readability fails
            clean_text = self._markdown_to_clean_text(markdown)
        
        # Store links and other metadata in seo_head as JSON
        metadata_dict = {
            "links": links,
            "source": "firecrawl",
            "content_type": "markdown",
            "firecrawl_metadata": metadata,  # Store the full Firecrawl metadata
            "markdown": markdown  # Store the original markdown for LLM usage
        }
        seo_head = json.dumps(metadata_dict)
        
        # Use clean_text for checksum (from readability, more stable)
        checksum = hashlib.sha256(clean_text.encode()).hexdigest()

        return PageAssets(
            url=url,
            raw_html=html,
            clean_text=clean_text,  # Use readability-extracted text for embedding
            seo_head=seo_head,      # Store metadata + markdown as JSON
            title=title,
        )

    def _markdown_to_clean_text(self, markdown: str) -> str:
        """
        Convert markdown to clean text optimized for semantic embedding.
        
        This method uses a deterministic approach to ensure consistent results:
        1. Normalizes line endings and whitespace first
        2. Applies transformations in a fixed order
        3. Uses consistent regex patterns
        4. Normalizes final output
        
        Args:
            markdown: Raw markdown content from Firecrawl
            
        Returns:
            Clean text optimized for semantic embedding
        """
        if not markdown:
            return ""
        
        # Step 1: Normalize line endings and basic whitespace
        text = markdown.replace('\r\n', '\n').replace('\r', '\n')
        
        # Step 2: Remove markdown formatting in a deterministic order
        # Headers
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        
        # Bold and italic (handle both * and _ consistently)
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'__(.*?)__', r'\1', text)
        text = re.sub(r'_(.*?)_', r'\1', text)
        
        # Links (extract text only)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # Lists (convert to consistent format)
        text = re.sub(r'^\s*[-*+]\s+', '• ', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        
        # Code blocks and inline code
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        
        # Blockquotes
        text = re.sub(r'^\s*>\s+', '', text, flags=re.MULTILINE)
        
        # Horizontal rules
        text = re.sub(r'^[-*_]{3,}$', '', text, flags=re.MULTILINE)
        
        # Step 3: Normalize whitespace deterministically
        # Replace all tabs with spaces
        text = text.replace('\t', ' ')
        
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        
        # Normalize line breaks (multiple newlines to double newlines)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Step 4: Remove dynamic content that changes between requests
        # Remove captcha questions (e.g., "What is 7 + 6?", "What is 4 x 7?")
        text = re.sub(r'What is \d+ [+\-*/] \d+\?', '', text)
        
        # Remove timestamps and dates that might be dynamic
        text = re.sub(r'\d{1,2}:\d{2}:\d{2}', '', text)  # Time stamps like 14:32:45
        text = re.sub(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', '', text)  # Full timestamps
        text = re.sub(r'Last updated:.*?\d{4}', '', text)  # "Last updated: 2025-01-15"
        text = re.sub(r'Updated:.*?\d{4}', '', text)  # "Updated: January 15, 2025"
        
        # Remove session IDs and random tokens (common patterns)
        text = re.sub(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', '', text)  # UUIDs
        text = re.sub(r'[a-f0-9]{32}', '', text)  # MD5 hashes
        text = re.sub(r'[a-f0-9]{40}', '', text)  # SHA1 hashes
        text = re.sub(r'[a-f0-9]{64}', '', text)  # SHA256 hashes
        
        # Remove random IDs and tokens
        text = re.sub(r'\b[a-zA-Z0-9]{16,}\b', '', text)  # Long random strings
        text = re.sub(r'session[_-]?id[=:]\s*[a-zA-Z0-9]+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'token[=:]\s*[a-zA-Z0-9]+', '', text, flags=re.IGNORECASE)
        
        # Remove JavaScript void links that might have dynamic content
        text = re.sub(r'javascript:void\(0\)', '', text)
        
        # Remove lines that are just numbers or very short random strings
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Skip lines that are just numbers or very short random content
            if re.match(r'^\d+$', line):  # Just numbers
                continue
            if re.match(r'^[a-zA-Z0-9]{1,3}$', line):  # Very short random strings
                continue
            if re.match(r'^[a-f0-9]{8}$', line):  # Short hex strings
                continue
                
            cleaned_lines.append(line)
        
        # Join lines with single newlines
        text = '\n'.join(cleaned_lines)
        
        # Final trim
        text = text.strip()
        
        return text