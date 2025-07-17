-- Complete Database Initialization Script
-- This script sets up the entire database schema for the webscraper project

-- Drop existing tables for a clean slate
DROP TABLE IF EXISTS chunks CASCADE;
DROP TABLE IF EXISTS keywords CASCADE;
DROP TABLE IF EXISTS pages CASCADE;

-- Enable the vector extension for pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the main pages table
CREATE TABLE pages (
    url                 text PRIMARY KEY,           -- Unique URL identifier
    title               text,                       -- Page title from HTML
    clean_text          text,                       -- Cleaned content from Firecrawl
    raw_html            text,                       -- Original HTML content
    markdown_checksum   text,                       -- SHA256 hash of markdown content
    markdown_changed    timestamptz,                -- When content last changed
    metadata            jsonb,                      -- Complete Firecrawl response data
    last_seen           timestamptz,                -- Last crawl timestamp
    summary_vec         vector(1024),               -- Page-level embedding
    embedded_at         timestamptz,                -- When embedding was created
    category            varchar(20),                -- Page category (content, hubs, etc.)
    category_confidence decimal(3,2)                -- Confidence in categorization
);

-- Create the chunks table for granular search
CREATE TABLE chunks (
    page_url    text REFERENCES pages(url) ON DELETE CASCADE,
    chunk_index integer,
    text        text,
    vec         vector(1024),
    PRIMARY KEY (page_url, chunk_index)
);

-- Create the keywords table
CREATE TABLE keywords (
    url         text REFERENCES pages(url) ON DELETE CASCADE,
    phrase      text NOT NULL,
    embedding   vector(1024)
);

-- Create HNSW index for fast vector similarity search
CREATE INDEX idx_chunks_vec ON chunks 
USING hnsw (vec vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Create indexes for efficient queries
CREATE INDEX idx_pages_markdown_checksum ON pages(markdown_checksum);
CREATE INDEX idx_pages_metadata ON pages USING GIN(metadata);
CREATE INDEX idx_pages_category ON pages(category);
CREATE INDEX idx_pages_category_confidence ON pages(category, category_confidence);

-- Add constraints for valid categories
ALTER TABLE pages ADD CONSTRAINT chk_category CHECK (
    category IN ('content', 'hubs', 'recruitment', 'interactable')
);

-- Add constraint for confidence range
ALTER TABLE pages ADD CONSTRAINT chk_confidence CHECK (
    category_confidence >= 0.0 AND category_confidence <= 1.0
);

-- Update existing pages with default category if not set
UPDATE pages SET category = 'content', category_confidence = 0.1 WHERE category IS NULL;

-- Add helpful comments
COMMENT ON TABLE pages IS 'Main table storing crawled web pages and their metadata';
COMMENT ON TABLE chunks IS 'Text chunks with vector embeddings for granular semantic search';
COMMENT ON TABLE keywords IS 'Keywords extracted from pages with their embeddings';
COMMENT ON COLUMN pages.markdown_checksum IS 'SHA256 hash of the markdown content from Firecrawl';
COMMENT ON COLUMN pages.markdown_changed IS 'Timestamp when markdown content last changed';
COMMENT ON COLUMN pages.metadata IS 'JSON metadata from Firecrawl (links, source, full response, etc.)';
COMMENT ON COLUMN pages.clean_text IS 'Cleaned markdown content from Firecrawl (ready for embedding)';
COMMENT ON COLUMN pages.category IS 'Page categorization (content, hubs, recruitment, interactable)';
COMMENT ON COLUMN pages.category_confidence IS 'Confidence score (0.0-1.0) for categorization';

-- Verify the setup
SELECT 'Database initialized successfully!' as status; 