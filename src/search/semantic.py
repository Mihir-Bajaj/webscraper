"""
Semantic search functionality for the webscraper project.
"""
from typing import List, Tuple, Optional
import sys
import psycopg2
from sentence_transformers import SentenceTransformer

from src.config.settings import DB_CONFIG, MODEL_CONFIG, SEARCH_CONFIG

class SemanticSearch:
    def __init__(self):
        self.model = SentenceTransformer(MODEL_CONFIG["name"])
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cur = self.conn.cursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cur.close()
        self.conn.close()

    def search(self, question: str, top_k: int = SEARCH_CONFIG["top_k"]) -> List[Tuple[str, str, float]]:
        """Search for semantically similar chunks."""
        # Encode the question
        q_vec = self.model.encode(
            question,
            normalize_embeddings=True
        ).tolist()

        # Configure HNSW search
        self.cur.execute(f"SET hnsw.ef_search = {SEARCH_CONFIG['ef_search']};")

        # Execute search query
        self.cur.execute(
            """
            WITH q AS (SELECT %s::vector AS v)
            SELECT c.page_url,
                   c.text,
                   1 - (c.vec <=> (SELECT v FROM q)) AS score
            FROM chunks c
            ORDER BY c.vec <=> (SELECT v FROM q)
            LIMIT %s
            """,
            (q_vec, top_k),
        )
        return self.cur.fetchall()

    def format_results(self, results: List[Tuple[str, str, float]]) -> str:
        """Format search results for display."""
        output = []
        for rank, (url, passage, score) in enumerate(results, 1):
            output.append(f"\n#{rank}  score={score:.3f}  {url}\n{passage[:300]}…")
        return "\n".join(output)

def main():
    if len(sys.argv) != 2:
        print("Usage: python -m src.search.semantic \"your question\"")
        sys.exit(1)

    question = sys.argv[1]
    with SemanticSearch() as search:
        results = search.search(question)
        print(search.format_results(results))

if __name__ == "__main__":
    main() 