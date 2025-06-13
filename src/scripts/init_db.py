"""
Database initialization script for the webscraper project.
"""
import psycopg2
from src.config.settings import DB_CONFIG

def init_db():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Create the vector extension if it doesn't exist
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Create the tables if they don't exist
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pages (
            url           text PRIMARY KEY,
            title         text,
            clean_text    text,
            content_checksum text,
            html_checksum    text,
            last_seen     timestamptz,
            content_changed timestamptz,
            html_changed    timestamptz,
            summary_vec   vector(768),  -- matches MPNet's size
            embedded_at   timestamptz
        );

        CREATE TABLE IF NOT EXISTS chunks (
            page_url      text REFERENCES pages(url) ON DELETE CASCADE,
            chunk_index   int,
            text          text,
            vec           vector(768),
            PRIMARY KEY (page_url, chunk_index)
        );
        """
    )

    # Create HNSW index for faster similarity search
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS chunks_vec_idx ON chunks 
        USING hnsw (vec vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
        """
    )

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database initialized successfully!")

if __name__ == "__main__":
    init_db() 