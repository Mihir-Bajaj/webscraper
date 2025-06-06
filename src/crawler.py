"""
crawler.py  –  dual-checksum site crawler
-----------------------------------------
DB schema requirements (table pages):
  url TEXT PRIMARY KEY
  title TEXT
  clean_text TEXT
  content_checksum TEXT
  html_checksum    TEXT
  last_seen        TIMESTAMPTZ
  content_changed  TIMESTAMPTZ
  html_changed     TIMESTAMPTZ
"""

import asyncio
import hashlib
import re
import time
from urllib.parse import urljoin, urlparse, urldefrag

import aiohttp
import psycopg2
from bs4 import BeautifulSoup
from readability import Document

# ───────────── configuration ────────────────────────────────────────────────
DB_CFG = dict(
    dbname="rag",
    user="postgres",
    password="postgres",
    host="localhost",
    port=5432,
)

MAX_DEPTH   = 2            # link-depth limit
MAX_PAGES   = 1_000        # hard stop
CRAWL_DELAY = 1.0          # seconds between hits
USER_AGENT  = "RAG-bot/0.1 (+https://example.com/bot-info)"

# ───────────── URL helpers ──────────────────────────────────────────────────
def canonical(url: str) -> str:
    """Lower-case host, drop fragments & query params → stable key."""
    u = urlparse(url)
    clean = u._replace(netloc=u.netloc.lower(), fragment="", query="").geturl()
    return clean.rstrip("/")


def iter_same_domain_links(base_url: str, html: str):
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        href = urldefrag(a["href"])[0]
        abs_url = urljoin(base_url, href)
        if urlparse(abs_url).netloc == urlparse(base_url).netloc:
            yield canonical(abs_url)

# ───────────── checksum builders ────────────────────────────────────────────
def compute_content_checksum(html: str) -> tuple[str, str]:
    """
    Returns (clean_text, sha256_of_clean_text).

    clean_text  =  title + meta description + alt text + visible article text.
    """
    # title (Document.short_title falls back to <h1> if <title> missing)
    title = Document(html).short_title().strip()

    # meta description
    soup_head = BeautifulSoup(html, "lxml").head
    meta_desc = ""
    if soup_head:
        tag = soup_head.find("meta", attrs={"name": re.compile("^description$", re.I)})
        if tag and tag.get("content"):
            meta_desc = tag["content"].strip()

    # main article
    main_html  = Document(html).summary()
    soup_body  = BeautifulSoup(main_html, "lxml")
    visible    = soup_body.get_text(" ", strip=True)

    # image alt text inside article
    alt_texts = " ".join(
        img.get("alt", "").strip()
        for img in soup_body.find_all("img")
        if img.get("alt")
    )

    parts = [title, meta_desc, alt_texts, visible]
    clean_text = re.sub(r"\s+", " ", " ".join(p for p in parts if p)).strip()
    checksum   = hashlib.sha256(clean_text.encode()).hexdigest()
    return clean_text, checksum


def compute_head_checksum(html: str) -> str:
    """
    Hash only stable, SEO-critical tags inside <head>.
    """
    soup = BeautifulSoup(html, "lxml")
    head = soup.head or BeautifulSoup("<head></head>", "lxml").head

    parts = []

    # <title>
    if head.title and head.title.string:
        parts.append(head.title.string.strip())

    # meta description / robots
    for name in ["description", "robots"]:
        tag = head.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            parts.append(f"{name}:{tag['content'].strip()}")

    # canonical
    canon = head.find("link", attrs={"rel": "canonical"})
    if canon and canon.get("href"):
        parts.append(f"canon:{canon['href'].strip()}")

    # hreflang alternates
    for al in head.find_all("link", attrs={"rel": "alternate", "hreflang": True}):
        parts.append(f"hl:{al['hreflang']}:{al.get('href','').strip()}")

    # JSON-LD structured data blocks
    for script in head.find_all("script", attrs={"type": "application/ld+json"}):
        parts.append(script.string.strip() if script.string else "")

    stable_head_text = " ".join(parts)
    return hashlib.sha256(stable_head_text.encode()).hexdigest()


# ───────────── DB UPSERT ────────────────────────────────────────────────────
def upsert_page(
    cur,
    *,
    url: str,
    title: str,
    clean_text: str,
    content_cs: str,
    head_cs: str,
) -> tuple[bool, bool]:
    """
    Returns (content_changed, html_changed)
    """
    cur.execute(
        """
        INSERT INTO pages (
          url, title, clean_text,
          content_checksum, html_checksum,
          last_seen, content_changed, html_changed
        )
        VALUES (%s,%s,%s,%s,%s,NOW(),NOW(),NOW())
        ON CONFLICT (url) DO NOTHING
        RETURNING 1;
        """,
        (url, title, clean_text, content_cs, head_cs),
    )
    if cur.fetchone():          # brand-new row
        return True, True

    cur.execute(
        "SELECT content_checksum, html_checksum FROM pages WHERE url = %s", (url,)
    )
    old_content, old_head = cur.fetchone()
    c_changed = old_content != content_cs
    h_changed = old_head    != head_cs

    cur.execute(
        """
        UPDATE pages
        SET last_seen = NOW(),
            title     = %s,
            clean_text = %s,
            content_checksum = %s,
            html_checksum    = %s,
            content_changed  = CASE WHEN %s THEN NOW() ELSE content_changed END,
            html_changed     = CASE WHEN %s THEN NOW() ELSE html_changed  END
        WHERE url = %s
        """,
        (title, clean_text, content_cs, head_cs, c_changed, h_changed, url),
    )
    return c_changed, h_changed

# ───────────── network fetch ────────────────────────────────────────────────
async def fetch(session: aiohttp.ClientSession, url: str):
    try:
        async with session.get(url, timeout=20) as resp:
            if resp.status != 200 or "text/html" not in resp.headers.get(
                "content-type", ""
            ):
                return None
            return await resp.text()
    except Exception:
        return None

# ───────────── crawl loop ───────────────────────────────────────────────────
async def crawl(start_url: str):
    queue   = [(start_url, 0)]
    visited = set()

    conn = psycopg2.connect(**DB_CFG)
    conn.autocommit = True
    cur = conn.cursor()

    async with aiohttp.ClientSession(headers={"User-Agent": USER_AGENT}) as session:
        while queue and len(visited) < MAX_PAGES:
            url, depth = queue.pop(0)
            if url in visited or depth > MAX_DEPTH:
                continue
            visited.add(url)

            html = await fetch(session, url)
            if html is None:
                continue

            clean_text, content_cs = compute_content_checksum(html)
            head_cs                = compute_head_checksum(html)
            title                  = Document(html).short_title()

            c_changed, h_changed = upsert_page(
                cur,
                url=url,
                title=title,
                clean_text=clean_text,
                content_cs=content_cs,
                head_cs=head_cs,
            )

            flag = (
                ("EMBD" if c_changed else "----")
                + (" SEO" if h_changed else "")
            )
            print(f"{flag:<8} {url}")

            # enqueue child links
            if depth < MAX_DEPTH:
                for link in iter_same_domain_links(url, html):
                    if link not in visited:
                        queue.append((link, depth + 1))

            time.sleep(CRAWL_DELAY)

    cur.close()
    conn.close()

# ───────────── entry point ──────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python crawler.py https://example.com")
        sys.exit(1)

    asyncio.run(crawl(canonical(sys.argv[1])))
