import psycopg2, textwrap
from psycopg2.extras import execute_values

conn = psycopg2.connect(
    dbname="rag", user="postgres", password="postgres", host="localhost", port=5432
)
cur = conn.cursor()

# 1) Create the two tables if they don’t exist yet
cur.execute(
    """
    CREATE TABLE IF NOT EXISTS pages (
      url           text PRIMARY KEY,
      checksum      text,
      last_seen     timestamptz,
      title         text,
      summary       text,
      summary_vec   vector(384),  -- matches MiniLM ’s size
      publish_date  date,
      intent_label  text
    );
    CREATE TABLE IF NOT EXISTS chunks (
      chunk_id      bigserial PRIMARY KEY,
      page_url      text REFERENCES pages(url) ON DELETE CASCADE,
      chunk_index   int,
      text          text,
      vec           vector(384)
    );
    """
)

# 2) Insert a dummy row (idempotent)
cur.execute(
    """
    INSERT INTO pages (url, checksum, last_seen)
    VALUES (%s, %s, NOW())
    ON CONFLICT (url) DO NOTHING
    """,
    ("https://example.com", "dummy"),
)
conn.commit()

# 3) Read it back
cur.execute("SELECT url, last_seen FROM pages LIMIT 1;")
print(cur.fetchone())

cur.close()
conn.close()
