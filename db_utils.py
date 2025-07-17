#!/usr/bin/env python3
"""
Database utilities for the webscraper project.
Consolidated script for database operations, checks, and maintenance.
"""

import psycopg2
import json
from psycopg2.extras import RealDictCursor
from src.config.settings import DB_CONFIG

def check_database_status():
    """Check overall database status and statistics."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        print("📊 Database Status Report")
        print("=" * 50)
        
        # Check pages table
        cur.execute("SELECT COUNT(*) FROM pages")
        total_pages = cur.fetchone()[0]
        print(f"📄 Total pages: {total_pages}")
        
        # Check embedded pages
        cur.execute("SELECT COUNT(*) FROM pages WHERE embedded_at IS NOT NULL")
        embedded_pages = cur.fetchone()[0]
        print(f"🔍 Embedded pages: {embedded_pages}")
        
        # Check chunks
        cur.execute("SELECT COUNT(*) FROM chunks")
        total_chunks = cur.fetchone()[0]
        print(f"📝 Total chunks: {total_chunks}")
        
        # Check categories
        cur.execute("""
            SELECT category, COUNT(*) as count, AVG(category_confidence) as avg_confidence
            FROM pages 
            WHERE category IS NOT NULL
            GROUP BY category 
            ORDER BY count DESC
        """)
        categories = cur.fetchall()
        print(f"\n🏷️  Page Categories:")
        for category, count, avg_conf in categories:
            print(f"   {category}: {count} pages (avg confidence: {avg_conf:.2f})")
        
        # Check recent pages
        cur.execute("""
            SELECT url, title, category, category_confidence, embedded_at
            FROM pages 
            ORDER BY last_seen DESC
            LIMIT 5
        """)
        recent_pages = cur.fetchall()
        print(f"\n🕒 Recent Pages:")
        for url, title, category, confidence, embedded_at in recent_pages:
            status = "✅" if embedded_at else "⏳"
            print(f"   {status} {url}")
            print(f"      Title: {title[:50]}...")
            print(f"      Category: {category} (confidence: {confidence:.2f})")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False

def check_metadata_structure():
    """Check if metadata contains full Firecrawl response."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        print("\n🔍 Metadata Structure Check")
        print("=" * 50)
        
        # Get a recent page with metadata
        cur.execute("""
            SELECT url, metadata 
            FROM pages 
            WHERE metadata IS NOT NULL 
            ORDER BY last_seen DESC 
            LIMIT 1
        """)
        
        result = cur.fetchone()
        if result:
            url = result['url']
            metadata = result['metadata']
            print(f"📄 Checking metadata for: {url}")
            
            if isinstance(metadata, dict):
                print("✅ Metadata is valid JSON")
                
                # Check for full response
                if "full_firecrawl_response" in metadata:
                    full_response = metadata["full_firecrawl_response"]
                    print("✅ Full Firecrawl response found!")
                    print(f"   Response keys: {list(full_response.keys())}")
                    
                    # Check expected fields
                    expected_fields = ["html", "markdown", "links", "metadata"]
                    missing_fields = [f for f in expected_fields if f not in full_response]
                    
                    if missing_fields:
                        print(f"⚠️  Missing fields: {missing_fields}")
                    else:
                        print("✅ All expected fields present!")
                else:
                    print("❌ Full Firecrawl response not found")
                    print(f"   Available keys: {list(metadata.keys())}")
            else:
                print("❌ Metadata is not a valid dictionary")
        else:
            print("❌ No pages with metadata found")
            
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Metadata check failed: {e}")
        return False

def initialize_database():
    """Initialize the database with the complete schema."""
    try:
        print("🚀 Initializing database...")
        
        # Read the SQL file
        with open('init_database.sql', 'r') as f:
            sql_content = f.read()
        
        # Split into individual statements (on semicolons)
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        for stmt in statements:
            try:
                cur.execute(stmt)
                conn.commit()
            except Exception as e:
                print(f"⚠️  Skipping statement due to error: {e}\nStatement: {stmt[:80]}...")
                conn.rollback()
        
        cur.close()
        conn.close()
        
        print("✅ Database initialized successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def main():
    """Main function to run database utilities."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python db_utils.py [command]")
        print("Commands:")
        print("  status     - Check database status and statistics")
        print("  metadata   - Check metadata structure")
        print("  init       - Initialize database schema")
        print("  all        - Run all checks")
        return
    
    command = sys.argv[1]
    
    if command == "status":
        check_database_status()
    elif command == "metadata":
        check_metadata_structure()
    elif command == "init":
        initialize_database()
    elif command == "all":
        print("🔍 Running all database checks...\n")
        check_database_status()
        check_metadata_structure()
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main() 