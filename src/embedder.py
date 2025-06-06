"""
embedder.py
-----------
• Embeds every page that is brand-new OR whose content_changed > embedded_at.
• Uses sentence-transformers/all-MiniLM-L6-v2 (384 dims, CPU-friendly).
• Stores page-level vector (summary_vec) and chunk vectors in `chunks`.
"""

import math, psycopg2, tiktoken, datetime
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from psycopg2.extras import execute_values

# ───── config ───────────────────────────────────────────────────────────────
DB   = dict(dbname="rag", user="postgres", password="postgres", host="localhost")
MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
CHUNK_TOKENS = 500
enc          = tiktoken.get_encoding("cl100k_base")      # same as OpenAI tiktoken
model        = SentenceTransformer(MODEL_NAME)

# ───── helpers ──────────────────────────────────────────────────────────────
def chunk_text(text: str, max_tokens=CHUNK_TOKENS):
    ids = enc.encode(text)
    for i in range(0, len(ids), max_tokens):
        yield enc.decode(ids[i : i + max_tokens]).strip()

# ───── main routine ─────────────────────────────────────────────────────────
def main():
    conn = psycopg2.connect(**DB)
    cur  = conn.cursor()

    cur.execute(
        """
        SELECT url, clean_text, content_changed, embedded_at
        FROM pages
        WHERE clean_text IS NOT NULL
          AND ( embedded_at IS NULL
             OR content_changed > embedded_at )
        """
    )
    targets = cur.fetchall()
    if not targets:
        print("✅  Nothing new to embed.")
        cur.close(); conn.close(); return

    print(f"🔍  {len(targets)} page(s) to embed …")

    for url, clean_text, content_ts, embedded_ts in tqdm(targets, desc="Pages"):
        if not clean_text:
            continue

        # ── 1. page-level embedding ────────────────────────────────────────
        page_vec = model.encode(clean_text,
                        show_progress_bar=False,
                        normalize_embeddings=True)
        cur.execute(
            """
            UPDATE pages
            SET summary_vec = %s,
                embedded_at = NOW()
            WHERE url = %s
            """,
            (page_vec.tolist(), url),
        )

        # ── 2. chunk-level embeddings ─────────────────────────────────────
        chunks = list(chunk_text(clean_text))
        if not chunks:
            continue

        vecs = model.encode(chunks,
                    show_progress_bar=False,
                    normalize_embeddings=True)
        rows = [
            (url, idx, chunk, vec.tolist())
            for idx, (chunk, vec) in enumerate(zip(chunks, vecs))
        ]
        execute_values(
            cur,
            """
            INSERT INTO chunks (page_url, chunk_index, text, vec)
            VALUES %s
            ON CONFLICT DO NOTHING
            """,
            rows,
        )
        conn.commit()

    cur.close(); conn.close()
    print("✅  Embedding pass complete.")

if __name__ == "__main__":
    main()
