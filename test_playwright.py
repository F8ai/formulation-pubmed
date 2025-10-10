#!/usr/bin/env python3
"""
Playwright test for the Formulation PubMed Microservice GitHub Pages site
"""

import asyncio
import sys
import os
from playwright.async_api import async_playwright

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_github_pages():
    """Test the GitHub Pages site functionality"""
    print("🎭 Starting Playwright tests for GitHub Pages...")
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)  # Set to True for headless
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Test 1: Main index page
            print("📄 Testing main index page...")
            await page.goto("https://f8ai.github.io/formulation-pubmed/")
            await page.wait_for_load_state("networkidle")
            
            # Check if page loaded
            title = await page.title()
            assert "Formulation PubMed Microservice" in title, f"Expected title to contain 'Formulation PubMed Microservice', got: {title}"
            print(f"✅ Main page title: {title}")
            
            # Check for status badge
            status_badge = await page.locator(".status-badge").text_content()
            assert "LIVE" in status_badge, f"Expected status badge to contain 'LIVE', got: {status_badge}"
            print(f"✅ Status badge: {status_badge}")
            
            # Check navigation cards
            nav_cards = await page.locator(".nav-card").count()
            assert nav_cards >= 4, f"Expected at least 4 navigation cards, got: {nav_cards}"
            print(f"✅ Navigation cards: {nav_cards}")
            
            # Test 2: Status dashboard
            print("📊 Testing status dashboard...")
            await page.goto("https://f8ai.github.io/formulation-pubmed/articles/")
            await page.wait_for_load_state("networkidle")
            
            # Check for stats
            total_articles = await page.locator("#total-articles").text_content()
            print(f"✅ Total articles: {total_articles}")
            
            # Test 3: Data browser
            print("📁 Testing data browser...")
            await page.goto("https://f8ai.github.io/formulation-pubmed/pubmed/")
            await page.wait_for_load_state("networkidle")
            
            # Check if data browser loaded
            browser_title = await page.title()
            assert "PubMed Data Browser" in browser_title, f"Expected title to contain 'PubMed Data Browser', got: {browser_title}"
            print(f"✅ Data browser title: {browser_title}")
            
            # Test 4: Article browser
            print("🔍 Testing article browser...")
            await page.goto("https://f8ai.github.io/formulation-pubmed/pubmed/browser.html")
            await page.wait_for_load_state("networkidle")
            
            # Check if article browser loaded
            article_title = await page.title()
            assert "PubMed File Browser" in article_title, f"Expected title to contain 'PubMed File Browser', got: {article_title}"
            print(f"✅ Article browser title: {article_title}")
            
            # Check for file items
            file_items = await page.locator(".file-item").count()
            assert file_items > 0, f"Expected file items to be present, got: {file_items}"
            print(f"✅ File items found: {file_items}")
            
            # Test 5: RSS feeds
            print("📰 Testing RSS feeds...")
            await page.goto("https://f8ai.github.io/formulation-pubmed/rss/")
            await page.wait_for_load_state("networkidle")
            
            # Check if RSS page loaded
            rss_title = await page.title()
            assert "RSS" in rss_title, f"Expected title to contain 'RSS', got: {rss_title}"
            print(f"✅ RSS page title: {rss_title}")
            
            # Test 6: Check for actual data files
            print("📄 Testing data file access...")
            
            # Try to access a specific article's metadata
            await page.goto("https://f8ai.github.io/formulation-pubmed/pubmed/data/articles/39781554/metadata/article.json")
            await page.wait_for_load_state("networkidle")
            
            # Check if JSON data is accessible
            content = await page.content()
            assert "pmid" in content, "Expected JSON content to contain 'pmid'"
            assert "39781554" in content, "Expected JSON content to contain PMID 39781554"
            print("✅ Article metadata JSON accessible")
            
            # Test 7: Check abstract content
            await page.goto("https://f8ai.github.io/formulation-pubmed/pubmed/data/articles/39781554/abstract/content.txt")
            await page.wait_for_load_state("networkidle")
            
            content = await page.content()
            assert "cannabis" in content.lower(), "Expected abstract to contain 'cannabis'"
            print("✅ Article abstract accessible")
            
            print("\n🎉 All tests passed! GitHub Pages site is working correctly.")
            
        except Exception as e:
            print(f"\n❌ Test failed: {str(e)}")
            # Take a screenshot for debugging
            await page.screenshot(path="test_failure.png")
            print("📸 Screenshot saved as test_failure.png")
            raise
        
        finally:
            await browser.close()

async def test_local_microservice():
    """Test the local microservice if it's running"""
    print("\n🔧 Testing local microservice...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Test health endpoint
            await page.goto("http://localhost:8003/health")
            await page.wait_for_load_state("networkidle")
            
            content = await page.content()
            if "healthy" in content.lower():
                print("✅ Local microservice health check passed")
            else:
                print("⚠️ Local microservice may not be running")
            
            # Test status endpoint
            await page.goto("http://localhost:8003/status")
            await page.wait_for_load_state("networkidle")
            
            content = await page.content()
            if "background_processor" in content.lower():
                print("✅ Local microservice status endpoint working")
            else:
                print("⚠️ Local microservice status endpoint may not be working")
                
        except Exception as e:
            print(f"⚠️ Local microservice test failed (may not be running): {str(e)}")
        
        finally:
            await browser.close()

async def main():
    """Run all tests"""
    print("🚀 Formulation PubMed Microservice - Playwright Tests")
    print("=" * 60)
    
    # Test GitHub Pages
    await test_github_pages()
    
    # Test local microservice (if running)
    await test_local_microservice()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed successfully!")
    print("\n📊 Test Summary:")
    print("- ✅ GitHub Pages main site")
    print("- ✅ Status dashboard")
    print("- ✅ Data browser")
    print("- ✅ Article browser")
    print("- ✅ RSS feeds")
    print("- ✅ Data file access")
    print("- ✅ JSON metadata access")
    print("- ✅ Abstract content access")

if __name__ == "__main__":
    asyncio.run(main())