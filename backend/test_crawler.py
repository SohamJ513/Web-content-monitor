# backend/test_fixed_crawler.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.crawler import ContentFetcher

def test_fixed_crawler():
    print("🚀 Testing Fixed Crawler")
    print("=" * 40)
    
    fetcher = ContentFetcher()
    
    # Test URLs
    test_urls = [
        "https://httpbin.org/html",
        "https://example.com",
        "https://docs.python.org/3/"
        "https://en.wikipedia.org/wiki/Machine_learning",
        "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference",
        "https://dev.to/t/machinelearning",
        "https://docs.python.org/3/whatsnew/index.html",
        "https://stackoverflow.blog/"
        "https://vcet.edu.in/"
    ]
    
    for url in test_urls:
        print(f"\n🔗 Testing URL: {url}")
        print("-" * 30)
        
        html, content = fetcher.fetch_and_extract(url)
        
        if html and content:
            print(f"✅ SUCCESS!")
            print(f"HTML length: {len(html)} characters")
            print(f"Content length: {len(content)} characters")
            print(f"Content preview: {content[:100]}...")
        elif html:
            print(f"⚠️ Got HTML but no content (length: {len(html)})")
        else:
            print("❌ Failed to fetch HTML")

if __name__ == "__main__":
    test_fixed_crawler()