"""
Checksum utilities for web content.

This module provides functions to compute checksums for different aspects of web content:
1. Full content checksums (text, title, meta description, image alt text)
2. SEO-related checksums (head tags, meta tags, canonical URLs, etc.)

The checksums are used to detect changes in content and SEO elements,
helping to determine when pages need to be re-embedded or re-indexed.

Example:
    ```python
    # Compute checksum for full content
    clean_text, content_hash = content_and_hash(html_content)
    
    # Compute checksum for SEO elements
    seo_hash = compute_head_checksum(html_content)
    ```
"""
import hashlib, re
from bs4 import BeautifulSoup
from readability import Document

def content_and_hash(html: str) -> tuple[str, str]:
    """
    Extract clean text content and compute its SHA-256 hash.
    
    This function:
    1. Extracts the page title
    2. Gets the meta description
    3. Extracts visible text content
    4. Collects image alt text
    5. Combines all text and computes a hash
    
    Args:
        html: The HTML content of the page
        
    Returns:
        Tuple of (clean_text, hash) where:
        - clean_text: Combined text content with extra whitespace removed
        - hash: SHA-256 hash of the clean text
        
    Example:
        >>> html = '''
        ... <html>
        ... <head><title>Example Page</title>
        ... <meta name="description" content="Example description">
        ... </head>
        ... <body>
        ... <img alt="Example image" src="img.jpg">
        ... <p>Main content</p>
        ... </body></html>
        ... '''
        >>> text, hash = content_and_hash(html)
        >>> text
        'Example Page Example description Example image Main content'
        >>> len(hash)
        64  # SHA-256 hash length
    """
    title = Document(html).short_title().strip()
    soup_head = BeautifulSoup(html, "lxml").head
    meta = soup_head.find("meta", attrs={"name": re.compile("^description$", re.I)}) \
           if soup_head else None
    meta_desc = meta["content"].strip() if meta and meta.get("content") else ""
    main_html = Document(html).summary()
    soup_body = BeautifulSoup(main_html, "lxml")
    visible = soup_body.get_text(" ", strip=True)
    alts = " ".join(img.get("alt","").strip()
                    for img in soup_body.find_all("img") if img.get("alt"))
    clean = re.sub(r"\s+", " ", " ".join(p for p in [title, meta_desc, alts, visible] if p)).strip()
    return clean, hashlib.sha256(clean.encode()).hexdigest()

def compute_head_checksum(html: str) -> str:
    """
    Compute SHA-256 hash of stable SEO elements in the page head.
    
    This function extracts and hashes SEO-critical elements:
    1. Page title
    2. Meta description and robots tags
    3. Canonical URL
    4. Hreflang alternate links
    5. JSON-LD structured data
    
    Args:
        html: The HTML content of the page
        
    Returns:
        SHA-256 hash of the combined SEO elements
        
    Example:
        >>> html = '''
        ... <html>
        ... <head>
        ... <title>Example Page</title>
        ... <meta name="description" content="Example description">
        ... <link rel="canonical" href="https://example.com/page">
        ... <script type="application/ld+json">
        ... {"@type": "WebPage", "name": "Example"}
        ... </script>
        ... </head>
        ... </html>
        ... '''
        >>> hash = compute_head_checksum(html)
        >>> len(hash)
        64  # SHA-256 hash length
    """
    soup = BeautifulSoup(html, "lxml")
    head = soup.head or BeautifulSoup("<head></head>", "lxml").head
    keep = []

    if head.title and head.title.string:
        keep.append(head.title.string.strip())

    for name in ["description", "robots"]:
        tag = head.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            keep.append(f"{name}:{tag['content'].strip()}")

    canon = head.find("link", attrs={"rel": "canonical"})
    if canon and canon.get("href"):
        keep.append(f"canon:{canon['href'].strip()}")

    for al in head.find_all("link", attrs={"rel": "alternate", "hreflang": True}):
        keep.append(f"hl:{al['hreflang']}:{al.get('href','').strip()}")

    for sc in head.find_all("script", attrs={"type": "application/ld+json"}):
        keep.append(sc.string.strip() if sc.string else "")

    stable = " ".join(keep)
    return hashlib.sha256(stable.encode()).hexdigest()