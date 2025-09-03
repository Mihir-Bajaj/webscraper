"""
Embedding generation and storage for the webscraper project.

This module handles the generation and storage of vector embeddings for web pages:
• Uses BGE-Large-EN model (1024 dimensions) for high-quality embeddings
• Splits content into chunks for granular semantic search
• Stores embeddings in PostgreSQL with pgvector extension
• Tracks embedding status to avoid redundant processing

Features:
- Page-level embeddings for overall content similarity
- Chunk-level embeddings for detailed semantic search
- Automatic change detection using markdown_checksum
- Efficient bulk operations with execute_values
- Progress tracking with tqdm

Example:
    ```python
    # Run embedding on all pages that need it
    python -m src.embedder.embedder
    
    # Or embed a single page programmatically
    with Embedder() as embedder:
        embedder.embed_page(
            "https://example.com",
            "This is the page content..."
        )
    ```
"""
import json
from typing import List, Optional
from sentence_transformers import SentenceTransformer
from urllib.parse import urlparse

from src.config.settings import REST_API_CONFIG, MODEL_CONFIG, CRAWLER_CONFIG, SEARCH_CONFIG
from src.embedder.chunker import TextChunker

class Embedder:
    """
    Handles the generation and storage of embeddings for web pages.
    
    This class manages the process of:
    1. Connecting to the database
    2. Loading the embedding model
    3. Generating embeddings for pages and chunks
    4. Storing embeddings in the database
    
    Attributes:
        model: The sentence transformer model for generating embeddings
        chunker: Utility for splitting text into chunks
        conn: Database connection
        cur: Database cursor
    """
    
    def __init__(self):
        """
        Initialize the embedder with model and REST API connection.
        
        Loads the sentence transformer model specified in MODEL_CONFIG
        and establishes a connection to the REST API.
        """
        import os
        from sentence_transformers import SentenceTransformer
        from huggingface_hub import snapshot_download
        
        # Check if model is already cached
        model_name = MODEL_CONFIG["name"]
        print(f"[INFO] Loading model: {model_name}")
        
        try:
            # Check if model files exist in cache
            # Use the standard HuggingFace cache location
            cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
            model_cache_path = os.path.join(cache_dir, "models--" + model_name.replace("/", "--"))
            
            if os.path.exists(model_cache_path):
                print(f"[INFO] Model found in cache: {model_cache_path}")
                print("[INFO] Using cached model (no download needed)")
            else:
                print(f"[INFO] Model not found in cache, will download to: {model_cache_path}")
                print("[INFO] This may take several minutes on first run...")
            
            # Load the model (will use cache if available)
            self.model = SentenceTransformer(model_name)
            print(f"[INFO] Model loaded successfully: {model_name}")
            
        except Exception as e:
            print(f"[ERROR] Failed to load model {model_name}: {e}")
            raise
        
        self.chunker = TextChunker()
        self.rest_config = REST_API_CONFIG

    def __enter__(self):
        """Context manager entry point."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point - no cleanup needed for REST API."""
        pass

    def get_targets(self) -> List[tuple]:
        """
        Get pages that need embedding via REST API.
        
        Queries the REST API for pages that either:
        1. Have never been embedded (embedded_at is NULL)
        2. Have been modified since last embedding (markdown_changed > embedded_at)
        
        Returns:
            List of tuples containing (url, clean_text, markdown_changed, embedded_at)
            
        Example:
            >>> embedder.get_targets()
            [
                ('https://example.com', 'Page content...', '2024-03-20 10:00:00', None),
                ('https://example.com/about', 'About page...', '2024-03-20 11:00:00', '2024-03-19 15:00:00')
            ]
        """
        import requests
        
        try:
            url = f"{self.rest_config['base_url']}/pages/for-embedding"
            response = requests.get(url, timeout=self.rest_config['timeout'])
            response.raise_for_status()
            data = response.json()
            
            # Handle the direct array response from the database API
            return [(page["url"], page["clean_text"], None, None) for page in data]
        except Exception as e:
            print(f"[ERROR] Exception in get_targets: {e}")
            return []

    def embed_page(self, url: str, clean_text: str) -> None:
        """
        Embed a single page and its chunks via REST API.
        
        This method:
        1. Generates a page-level embedding for the entire content
        2. Splits the content into chunks
        3. Generates embeddings for each chunk
        4. Stores all embeddings via REST API
        
        Args:
            url: The URL of the page being embedded
            clean_text: The cleaned text content of the page
            
        Example:
            >>> embedder.embed_page(
            ...     "https://example.com",
            ...     "This is the page content. It will be split into chunks..."
            ... )
            # Will:
            # 1. Generate embedding for full text
            # 2. Split into chunks of MODEL_CONFIG["chunk_tokens"] tokens
            # 3. Generate embeddings for each chunk
            # 4. Store all embeddings via REST API
        """
        if not clean_text:
            return

        # 1. Page-level embedding
        page_vec = self.model.encode(
            clean_text,
            show_progress_bar=False,
            normalize_embeddings=True
        )

        # 2. Chunk-level embeddings
        chunks = self.chunker.chunk_text(clean_text)
        if not chunks:
            return

        vecs = self.model.encode(
            chunks,
            show_progress_bar=False,
            normalize_embeddings=True
        )
        
        # Prepare batch data for REST API
        # Extract page_id from the URL by getting the page from the database
        import requests
        from urllib.parse import quote
        
        # Use the original URL (not canonicalized) since the database stores URLs with www
        # The crawler stores the original URLs from Firecrawl, not canonicalized ones
        original_url = url
        
        try:
            # URL encode the original URL for the API call
            encoded_url = quote(original_url, safe='')
            page_response = requests.get(f"{self.rest_config['base_url']}/pages/url/{encoded_url}", timeout=self.rest_config['timeout'])
            if page_response.status_code == 200:
                page_info = page_response.json()
                if page_info:
                    page_id = page_info["id"]
                else:
                    print(f"[WARNING] Could not find page_id for URL: {original_url}")
                    return
            else:
                print(f"[WARNING] Could not fetch page info for URL: {original_url}")
                return
        except Exception as e:
            print(f"[ERROR] Exception getting page_id: {e}")
            return

        # Prepare chunks data for our database API
        chunks_data = [
            {
                "chunk_index": i,
                "text": chunk,
                "vec": vec.tolist()
            }
            for i, (chunk, vec) in enumerate(zip(chunks, vecs))
        ]
        
        # Store chunks using the chunks batch endpoint
        try:
            chunks_url = f"{self.rest_config['base_url']}/chunks/batch"
            chunks_response = requests.post(chunks_url, 
                params={"page_url": url},
                json=chunks_data,
                timeout=self.rest_config['timeout'])
            chunks_response.raise_for_status()
        except Exception as e:
            print(f"[ERROR] Exception storing chunks: {e}")
            raise

        # Update page with summary vector using the vectors embed endpoint
        embed_data = {
            "url": url,
            "page_vector": page_vec.tolist(),
            "chunks": [
                {
                    "text": chunk,
                    "vector": vec.tolist()
                }
                for chunk, vec in zip(chunks, vecs)
            ]
        }
        
        # Send to REST API
        try:
            embed_url = f"{self.rest_config['base_url']}/vectors/embed"
            response = requests.post(embed_url, json=embed_data, timeout=self.rest_config['timeout'])
            response.raise_for_status()
        except Exception as e:
            print(f"[ERROR] Exception in embed_page: {e}")
            raise

    def run(self) -> None:
        """
        Run the embedding process on all pages that need embedding.
        
        This method:
        1. Gets all pages that need embedding
        2. Processes each page with a progress bar
        3. Generates and stores embeddings for each page
        
        Example:
            >>> embedder.run()
            🔍  5 page(s) to embed …
            Pages: 100%|██████████| 5/5 [00:30<00:00, 6.00s/page]
            ✅  Embedding pass complete.
        """
        targets = self.get_targets()
        if not targets:
            print("✅  Nothing new to embed.")
            return

        print(f"🔍  {len(targets)} page(s) to embed …")
        for url, clean_text, content_ts, embedded_ts in targets:
            self.embed_page(url, clean_text)
        print("✅  Embedding pass complete.")

    def _canonicalize_url(self, url: str) -> str:
        """
        Canonicalize a URL to match the crawler's canonicalization.
        
        This method uses the same logic as Crawler.canonical() to ensure
        URLs are handled consistently between crawler and embedder.
        
        Args:
            url: The URL to canonicalize
            
        Returns:
            The canonicalized URL
        """
        from urllib.parse import parse_qs, urlencode, urlparse
        
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
    def is_crawlable_url(url: str) -> bool:
        # Only allow http(s) URLs
        return url.startswith("http://") or url.startswith("https://")

def is_same_domain(url1, url2):
    def strip_www(netloc):
        return netloc.lower().lstrip('www.')
    return strip_www(urlparse(url1).netloc) == strip_www(urlparse(url2).netloc)

def main():
    """
    Main entry point for the embedder script.
    
    Creates an Embedder instance and runs the embedding process
    on all pages that need embedding.
    
    Example:
        $ python -m src.embedder.embedder
        🔍  5 page(s) to embed …
        Pages: 100%|██████████| 5/5 [00:30<00:00, 6.00s/page]
        ✅  Embedding pass complete.
    """
    with Embedder() as embedder:
        embedder.run()

if __name__ == "__main__":
    main() 