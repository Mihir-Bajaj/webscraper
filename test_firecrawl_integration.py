#!/usr/bin/env python3
"""
Test script to verify Firecrawl integration with webscraper.
"""

import asyncio
import aiohttp
from src.crawler.crawler import Crawler

async def test_firecrawl_fetcher():
    """Test the FirecrawlFetcher with a simple URL."""
    print("Testing FirecrawlFetcher integration...")
    
    # Create a crawler instance
    crawler = Crawler()
    
    # Test URL
    test_url = "https://example.com"
    
    print(f"Starting crawl of {test_url}")
    print("This will use the Firecrawl server for fetching...")
    
    try:
        # Start the crawl
        await crawler.crawl(test_url)
        print("✅ Crawl completed successfully!")
        
    except Exception as e:
        print(f"❌ Crawl failed: {e}")
        return False
    
    return True

async def test_firecrawl_api_directly():
    """Test the Firecrawl API directly to ensure it's working."""
    print("\nTesting Firecrawl API directly...")
    
    url = "http://localhost:3002/v1"
    test_url = "https://example.com"
    
    async with aiohttp.ClientSession() as session:
        try:
            # Test the scrape endpoint
            body = {
                "url": test_url,
                "formats": ["html", "markdown", "links"],
                "onlyMainContent": True,
                "excludeTags": ["img", "video"],
                "fastMode": False
            }
            
            print(f"POSTing to {url}/scrape...")
            async with session.post(f"{url}/scrape", json=body) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        print("✅ Scrape completed successfully!")
                        print(f"Got HTML length: {len(data.get('data', {}).get('html', ''))}")
                        print(f"Got markdown length: {len(data.get('data', {}).get('markdown', ''))}")
                        print(f"Got {len(data.get('data', {}).get('links', []))} links")
                        return True
                    else:
                        print(f"❌ Scrape failed: {data.get('error', 'Unknown error')}")
                        return False
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to scrape: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            print(f"❌ API test failed: {e}")
            return False

async def main():
    """Main test function."""
    print("🚀 Starting Firecrawl integration tests...\n")
    
    # Test 1: Direct API test
    api_success = await test_firecrawl_api_directly()
    
    if not api_success:
        print("\n❌ Firecrawl API test failed. Please check if the server is running.")
        return
    
    print("\n" + "="*50)
    
    # Test 2: Integration test
    integration_success = await test_firecrawl_fetcher()
    
    if integration_success:
        print("\n🎉 All tests passed! Firecrawl integration is working correctly.")
    else:
        print("\n❌ Integration test failed.")

if __name__ == "__main__":
    asyncio.run(main()) 