"""
Main embedding logic for the webscraper project.

This module handles the generation and storage of embeddings for web pages and their content chunks.
It uses sentence-transformers to create vector embeddings that can be used for semantic search.

The embedding process:
1. Identifies pages that need embedding (new or changed content)
2. Generates page-level embeddings for the entire content
3. Splits content into chunks and generates chunk-level embeddings
4. Stores embeddings in a PostgreSQL database

Example:
    ```python
    # Run the embedder on all pages that need embedding
    with Embedder() as embedder:
        embedder.run()
    
    # Or embed a single page
    with Embedder() as embedder:
        embedder.embed_page(
            "https://example.com",
            "This is the page content..."
        )
    ```
"""
from typing import List, Optional
import psycopg2
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from psycopg2.extras import execute_values

from src.config.settings import DB_CONFIG, MODEL_CONFIG, ENCODER_CLS
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
        Initialize the embedder with model and database connection.
        
        Loads the sentence transformer model specified in MODEL_CONFIG
        and establishes a connection to the PostgreSQL database.
        """
        self.model = SentenceTransformer(MODEL_CONFIG["name"])
        self.chunker = TextChunker()
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cur = self.conn.cursor()

    def __enter__(self):
        """Context manager entry point."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point - closes database connections."""
        self.cur.close()
        self.conn.close()

    def get_targets(self) -> List[tuple]:
        """
        Get pages that need embedding.
        
        Queries the database for pages that either:
        1. Have never been embedded (embedded_at is NULL)
        2. Have been modified since last embedding (content_changed > embedded_at)
        
        Returns:
            List of tuples containing (url, clean_text, content_changed, embedded_at)
            
        Example:
            >>> embedder.get_targets()
            [
                ('https://example.com', 'Page content...', '2024-03-20 10:00:00', None),
                ('https://example.com/about', 'About page...', '2024-03-20 11:00:00', '2024-03-19 15:00:00')
            ]
        """
        self.cur.execute(
            """
            SELECT url, clean_text, content_changed, embedded_at
            FROM pages
            WHERE clean_text IS NOT NULL
              AND (embedded_at IS NULL OR content_changed > embedded_at)
            """
        )
        return self.cur.fetchall()

    def embed_page(self, url: str, clean_text: str) -> None:
        """
        Embed a single page and its chunks.
        
        This method:
        1. Generates a page-level embedding for the entire content
        2. Splits the content into chunks
        3. Generates embeddings for each chunk
        4. Stores all embeddings in the database
        
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
            # 4. Store all embeddings in database
        """
        if not clean_text:
            return

        # 1. Page-level embedding
        page_vec = self.model.encode(
            clean_text,
            show_progress_bar=False,
            normalize_embeddings=True
        )
        self.cur.execute(
            """
            UPDATE pages
            SET summary_vec = %s,
                embedded_at = NOW()
            WHERE url = %s
            """,
            (page_vec.tolist(), url),
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
        
        rows = [
            (url, idx, chunk, vec.tolist())
            for idx, (chunk, vec) in enumerate(zip(chunks, vecs))
        ]
        
        execute_values(
            self.cur,
            """
            INSERT INTO chunks (page_url, chunk_index, text, vec)
            VALUES %s
            ON CONFLICT DO NOTHING
            """,
            rows,
        )
        self.conn.commit()

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
        for url, clean_text, content_ts, embedded_ts in tqdm(targets, desc="Pages"):
            self.embed_page(url, clean_text)
        print("✅  Embedding pass complete.")

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