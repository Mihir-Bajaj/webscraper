"""
Semantic search functionality for the webscraper project.

This module provides semantic search capabilities using:
• BGE-Large-EN model (1024 dimensions) for high-quality embeddings
• PostgreSQL with pgvector extension for efficient similarity search
• HNSW index for fast approximate nearest neighbor search
• Configurable search parameters for optimal results

Features:
- Vector similarity search using cosine distance
- Configurable top-k results and search precision
- Formatted output with scores and content previews
- Command-line interface for easy testing

Example:
    ```python
    # Search from command line
    python -m src.search.semantic "custom software development"
    
    # Search programmatically
    with SemanticSearch() as search:
        results = search.search("custom software development", top_k=5)
        print(search.format_results(results))
    ```
"""
from typing import List, Tuple, Optional
import sys
from sentence_transformers import SentenceTransformer

from src.config.settings import REST_API_CONFIG, MODEL_CONFIG, SEARCH_CONFIG

class SemanticSearch:
    def __init__(self):
        self.model = SentenceTransformer(MODEL_CONFIG["name"])
        self.rest_config = REST_API_CONFIG

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def search(self, question: str, top_k: int = SEARCH_CONFIG["top_k"]) -> List[Tuple[str, str, float]]:
        """Search for semantically similar chunks via REST API."""
        # Encode the question
        q_vec = self.model.encode(
            question,
            normalize_embeddings=True
        ).tolist()

        # Execute search via REST API
        import requests
        try:
            url = f"{self.rest_config['base_url']}/vectors/search"
            data = {
                "vector": q_vec,
                "limit": top_k
            }
            response = requests.post(url, json=data, timeout=self.rest_config['timeout'])
            response.raise_for_status()
            result = response.json()
            
            # Convert to expected format (url, text, score)
            search_results = result.get("data", {}).get("pages", [])
            return [(item["url"], item.get("clean_text", "")[:300], item.get("similarity", 0.0)) for item in search_results]
        except Exception as e:
            print(f"[ERROR] Exception in search: {e}")
            return []

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