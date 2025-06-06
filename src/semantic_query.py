"""
python semantic_query.py "your question here"
Returns top-k chunks + their parent URL.
"""

import sys, psycopg2, json
from sentence_transformers import SentenceTransformer

DB = dict(dbname="rag", user="postgres", password="postgres", host="localhost")
MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
TOP_K = 5

def main(question: str):
    model = SentenceTransformer(MODEL_NAME)
    q_vec = model.encode(question, normalize_embeddings=True).tolist()

    conn = psycopg2.connect(**DB)
    cur  = conn.cursor()
    cur.execute("SET hnsw.ef_search = 200;")

    # ↓ pgvector cosine distance operator <=>  (smaller = closer)
    cur.execute(
        """
        WITH q AS (SELECT %s::vector AS v)
        SELECT c.page_url,
               c.text,
               1 - (c.vec <=> (SELECT v FROM q)) AS score
        FROM chunks c
        ORDER BY c.vec <=> (SELECT v FROM q)
        LIMIT %s
        """,
        (q_vec, TOP_K),
    )
    rows = cur.fetchall()

    for rank, (url, passage, score) in enumerate(rows, 1):
        print(f"\n#{rank}  score={score:.3f}  {url}\n{passage[:300]}…")

    cur.close(); conn.close()

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Usage: python semantic_query.py \"your question\"")
        sys.exit(1)
    main(sys.argv[1])
