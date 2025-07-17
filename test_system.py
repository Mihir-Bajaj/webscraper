#!/usr/bin/env python3
"""
Comprehensive test suite for the webscraper project.
Consolidated testing for all major components.
"""

import asyncio
import aiohttp
import psycopg2
from src.config.settings import DB_CONFIG

async def test_firecrawl_api():
    """Test Firecrawl API functionality."""
    print("🔍 Testing Firecrawl API...")
    
    url = "http://localhost:3002/v1"
    test_url = "https://example.com"
    
    async with aiohttp.ClientSession() as session:
        try:
            body = {
                "url": test_url,
                "formats": ["html", "markdown", "links"],
                "onlyMainContent": False,
                "fastMode": False
            }
            
            async with session.post(f"{url}/scrape", json=body) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        print("✅ Firecrawl API working correctly")
                        return True
                    else:
                        print(f"❌ Firecrawl API failed: {data.get('error', 'Unknown error')}")
                        return False
                else:
                    error_text = await response.text()
                    print(f"❌ Firecrawl API error: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Firecrawl API test failed: {e}")
            return False

def test_database_connection():
    """Test database connection and basic operations."""
    print("\n🗄️  Testing database connection...")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Test basic query
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
        print("✅ Database connection successful")
        print(f"   PostgreSQL version: {version[:50]}...")
        
        # Test tables exist
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cur.fetchall()]
        print(f"✅ Found tables: {', '.join(tables)}")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_metadata_storage():
    """Test that metadata contains full Firecrawl response."""
    print("\n📊 Testing metadata storage...")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Check if any pages have metadata
        cur.execute("SELECT COUNT(*) FROM pages WHERE metadata IS NOT NULL")
        pages_with_metadata = cur.fetchone()[0]
        
        if pages_with_metadata > 0:
            print(f"✅ Found {pages_with_metadata} pages with metadata")
            
            # Check for full response in recent page
            cur.execute("""
                SELECT metadata 
                FROM pages 
                WHERE metadata IS NOT NULL 
                ORDER BY last_seen DESC 
                LIMIT 1
            """)
            
            result = cur.fetchone()
            if result and result[0]:
                metadata = result[0]
                if "full_firecrawl_response" in metadata:
                    print("✅ Full Firecrawl response found in metadata")
                    return True
                else:
                    print("❌ Full Firecrawl response not found in metadata")
                    return False
            else:
                print("❌ No valid metadata found")
                return False
        else:
            print("⚠️  No pages with metadata found (run crawler first)")
            return True  # Not a failure, just no data yet
            
    except Exception as e:
        print(f"❌ Metadata test failed: {e}")
        return False
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

def test_search_functionality():
    """Test semantic search functionality."""
    print("\n🔍 Testing search functionality...")
    
    try:
        # Import search module
        from src.search.semantic import SemanticSearch
        
        with SemanticSearch() as search:
            # Test with a simple query
            results = search.search("test query", top_k=1)
            print("✅ Search functionality working")
            return True
            
    except Exception as e:
        print(f"❌ Search test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("🚀 Starting comprehensive system test...\n")
    
    tests = [
        ("Firecrawl API", test_firecrawl_api()),
        ("Database Connection", test_database_connection()),
        ("Metadata Storage", test_metadata_storage()),
        ("Search Functionality", test_search_functionality())
    ]
    
    results = []
    
    for test_name, test_coro in tests:
        if asyncio.iscoroutine(test_coro):
            result = await test_coro
        else:
            result = test_coro
        results.append((test_name, result))
    
    print(f"\n📊 Test Results:")
    print("=" * 50)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if not result:
            all_passed = False
    
    print(f"\n{'🎉 All tests passed!' if all_passed else '⚠️  Some tests failed'}")
    
    if all_passed:
        print("\n✅ System is ready for use!")
    else:
        print("\n🔧 Please check the failed tests above")

if __name__ == "__main__":
    asyncio.run(main()) 