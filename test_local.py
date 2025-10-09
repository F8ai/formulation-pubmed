#!/usr/bin/env python3
"""
Test script to verify the formulation-pubmed microservice is working locally
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.pubmed_scraper import PubMedScraper
from src.data_processor import DataProcessor
from src.storage_manager import StorageManager
from src.background_processor import BackgroundProcessor

async def test_pubmed_scraper():
    """Test PubMed scraper"""
    print("🔍 Testing PubMed Scraper...")
    
    scraper = PubMedScraper()
    
    # Test search with a simple term
    articles = await scraper.search_articles(
        term="cannabis formulation",
        max_results=5,
        date_range={'start_year': 2023, 'end_year': 2024}
    )
    
    print(f"✅ Found {len(articles)} articles")
    
    if articles:
        article = articles[0]
        print(f"   Sample article: {article.get('title', 'No title')[:100]}...")
        print(f"   PMID: {article.get('pmid', 'No PMID')}")
        print(f"   Journal: {article.get('journal', 'No journal')}")
    
    return len(articles) > 0

async def test_data_processor():
    """Test data processor"""
    print("\n🔄 Testing Data Processor...")
    
    processor = DataProcessor()
    
    # Create sample article data
    sample_article = {
        'pmid': '12345678',
        'title': 'Cannabis Formulation for Pharmaceutical Applications',
        'abstract': 'This study examines cannabis formulation techniques for pharmaceutical use, including extraction methods and stability testing.',
        'authors': ['Smith, J.', 'Doe, A.'],
        'journal': 'Journal of Cannabis Research',
        'publication_date': '2024-01-15',
        'doi': '10.1234/example',
        'keywords': ['cannabis', 'formulation', 'pharmaceutical'],
        'mesh_terms': ['Cannabis', 'Pharmaceutical Preparations'],
        'url': 'https://pubmed.ncbi.nlm.nih.gov/12345678/'
    }
    
    # Process the article
    processed_articles = processor.process_articles([sample_article])
    
    if processed_articles:
        article = processed_articles[0]
        print(f"✅ Processed article with relevance score: {article.get('relevance_score', 0):.2f}")
        print(f"   Formulation relevance: {article.get('formulation_relevance', {}).get('relevance_level', 'unknown')}")
        print(f"   Cannabis relevance: {article.get('cannabis_relevance', {}).get('relevance_level', 'unknown')}")
        print(f"   Extracted entities: {list(article.get('extracted_entities', {}).keys())}")
        return True
    else:
        print("❌ No processed articles returned")
        return False

async def test_storage_manager():
    """Test storage manager"""
    print("\n💾 Testing Storage Manager...")
    
    storage = StorageManager()
    
    # Test storing sample data
    sample_data = {
        'pmid': '12345678',
        'title': 'Test Article',
        'abstract': 'This is a test abstract',
        'full_text': 'This is test full text content',
        'full_text_source': 'test',
        'download_timestamp': datetime.now().isoformat()
    }
    
    # Store the data
    success = await storage.store_article_fulltext('12345678', sample_data)
    
    if success:
        print("✅ Successfully stored test article")
        
        # Try to retrieve it
        retrieved = await storage.get_article_fulltext('12345678')
        if retrieved:
            print("✅ Successfully retrieved test article")
            return True
        else:
            print("❌ Failed to retrieve test article")
            return False
    else:
        print("❌ Failed to store test article")
        return False

async def test_background_processor():
    """Test background processor initialization"""
    print("\n🔄 Testing Background Processor...")
    
    # Load config
    with open('data/pubmed.json', 'r') as f:
        config = json.load(f)
    
    storage = StorageManager()
    processor = BackgroundProcessor(config, storage)
    
    print("✅ Background processor initialized")
    print(f"   Processed PMIDs: {len(processor.processed_pmids)}")
    print(f"   Running: {processor.running}")
    
    return True

async def main():
    """Run all tests"""
    print("🚀 Testing Formulation PubMed Microservice Components\n")
    
    tests = [
        ("PubMed Scraper", test_pubmed_scraper),
        ("Data Processor", test_data_processor),
        ("Storage Manager", test_storage_manager),
        ("Background Processor", test_background_processor)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with error: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("📊 TEST SUMMARY")
    print("="*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("\n🎉 All tests passed! The microservice is ready to run.")
        print("\nNext steps:")
        print("1. Create GitHub repository: https://github.com/f8ai/formulation-pubmed")
        print("2. Push code: git remote add origin https://github.com/f8ai/formulation-pubmed.git && git push -u origin main")
        print("3. Deploy to AWS App Runner")
        print("4. Monitor at /health and /status endpoints")
    else:
        print(f"\n⚠️  {len(results) - passed} tests failed. Please check the errors above.")

if __name__ == "__main__":
    asyncio.run(main())