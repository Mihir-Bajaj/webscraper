-- Migration script to update pages table for Firecrawl-based pipeline
-- This removes HTML-related columns and adds metadata storage

-- 1. Add new columns
ALTER TABLE pages ADD COLUMN IF NOT EXISTS markdown_checksum TEXT;
ALTER TABLE pages ADD COLUMN IF NOT EXISTS markdown_changed TIMESTAMP WITH TIME ZONE;
ALTER TABLE pages ADD COLUMN IF NOT EXISTS metadata JSONB;

-- 2. Copy existing content checksum data to new markdown_checksum column
UPDATE pages SET markdown_checksum = content_checksum WHERE markdown_checksum IS NULL;

-- 3. Copy existing content_changed data to new markdown_changed column
UPDATE pages SET markdown_changed = content_changed WHERE markdown_changed IS NULL;

-- 4. Drop old columns
ALTER TABLE pages DROP COLUMN IF EXISTS html_checksum;
ALTER TABLE pages DROP COLUMN IF EXISTS html_changed;
ALTER TABLE pages DROP COLUMN IF EXISTS content_checksum;
ALTER TABLE pages DROP COLUMN IF EXISTS content_changed;

-- 5. Add constraints and indexes
CREATE INDEX IF NOT EXISTS idx_pages_markdown_checksum ON pages(markdown_checksum);
CREATE INDEX IF NOT EXISTS idx_pages_metadata ON pages USING GIN(metadata);

-- 6. Update the summary_vec NULL check to use new column name
-- (This will be handled in the Python code)

COMMENT ON COLUMN pages.markdown_checksum IS 'SHA256 hash of the markdown content from Firecrawl';
COMMENT ON COLUMN pages.markdown_changed IS 'Timestamp when markdown content last changed';
COMMENT ON COLUMN pages.metadata IS 'JSON metadata from Firecrawl (links, source, etc.)';
COMMENT ON COLUMN pages.clean_text IS 'Cleaned markdown content from Firecrawl (ready for embedding)'; 